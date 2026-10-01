#!/usr/bin/env python3

"""业务层自测：覆盖因果合并、冲突、过期、快照审核、发布回滚、批量原子性与幂等。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


BASE_URL = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"
PASSED = 0
TOTAL = 0


def request(method: str, path: str, payload: Any = None) -> tuple[int, Any]:
    raw = None if payload is None else json.dumps(payload).encode("utf-8")
    outgoing = urllib.request.Request(
        BASE_URL + path,
        data=raw,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(outgoing, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def check(name: str, condition: bool, detail: object = "") -> None:
    global PASSED, TOTAL
    TOTAL += 1
    if condition:
        PASSED += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name}: {detail}")


def reset() -> None:
    request("POST", "/admin/reset", {})


def new_plan(name: str = "plan", reviewers: list[str] | None = None) -> str:
    _, plan = request(
        "POST",
        "/plans",
        {
            "name": name,
            "required_reviewer_ids": reviewers or ["reviewer-a"],
            "idempotency_key": f"plan-{name}",
        },
    )
    return plan["id"]


def submit(plan_id: str, key: str, **fields: Any) -> tuple[int, Any]:
    body = {"idempotency_key": key, **fields}
    return request("POST", f"/plans/{plan_id}/operations", body)


def code(body: Any) -> str:
    return body.get("error", {}).get("code", "")


# --- 1. 顺序接纳与隐式因果链 ---
reset()
plan = new_plan("causal")
status, first = submit(
    plan, "k1", operation_id="op-a1", actor_id="alice", actor_sequence=1,
    kind="set_title", payload={"value": "一级响应"},
)
check("首条操作直接接纳", status == 201 and first["state"] == "ACCEPTED", first)

status, third = submit(
    plan, "k3", operation_id="op-a3", actor_id="alice", actor_sequence=3,
    kind="set_title", payload={"value": "三级响应"},
)
check("缺前驱时进入 PENDING", status == 201 and third["state"] == "PENDING", third)

_, view = request("GET", f"/plans/{plan}")
check("待定操作体现在视图", view["pending_operation_ids"] == ["op-a3"], view)
check("标题取已接纳的值", view["title"] == "一级响应", view)

status, second = submit(
    plan, "k2", operation_id="op-a2", actor_id="alice", actor_sequence=2,
    kind="set_title", payload={"value": "二级响应"},
)
_, view = request("GET", f"/plans/{plan}")
_, third_now = request("GET", "/operations/op-a3")
check(
    "补齐前驱后级联接纳",
    second["state"] == "ACCEPTED"
    and third_now["state"] == "ACCEPTED"
    and view["pending_operation_ids"] == []
    and view["title"] == "三级响应"
    and view["head_operation_ids"] == ["op-a3"],
    {"view": view, "op": third_now},
)

# --- 2. 并发标量冲突 ---
reset()
plan = new_plan("conflict")
submit(plan, "c0", operation_id="base", actor_id="alice", actor_sequence=1,
       kind="set_title", payload={"value": "底稿"})
submit(plan, "c1", operation_id="left", actor_id="bob", actor_sequence=1,
       parent_operation_ids=["base"], kind="set_title", payload={"value": "左"})
submit(plan, "c2", operation_id="right", actor_id="carol", actor_sequence=1,
       parent_operation_ids=["base"], kind="set_title", payload={"value": "右"})
_, view = request("GET", f"/plans/{plan}")
check(
    "并发改同一字段产生冲突",
    view["title"] is None
    and view["field_conflicts"] == [
        {"field": "title", "operation_ids": ["left", "right"], "values": ["右", "左"]}
    ],
    view,
)
status, blocked = request(
    "POST", f"/plans/{plan}/snapshots", {"idempotency_key": "snap-blocked"}
)
check(
    "有冲突时禁止建快照",
    status == 409 and code(blocked) == "PLAN_NOT_SNAPSHOTTABLE",
    blocked,
)

submit(plan, "c3", operation_id="merge", actor_id="bob", actor_sequence=2,
       parent_operation_ids=["left", "right"], kind="set_title",
       payload={"value": "合并稿"})
_, view = request("GET", f"/plans/{plan}")
check(
    "后继操作解决冲突",
    view["title"] == "合并稿" and view["field_conflicts"] == [],
    view,
)

# --- 3. 相同值的并发不算冲突 ---
reset()
plan = new_plan("same-value")
submit(plan, "s0", operation_id="s-base", actor_id="alice", actor_sequence=1,
       kind="set_severity", payload={"value": "LOW"})
submit(plan, "s1", operation_id="s-left", actor_id="bob", actor_sequence=1,
       parent_operation_ids=["s-base"], kind="set_severity", payload={"value": "HIGH"})
submit(plan, "s2", operation_id="s-right", actor_id="carol", actor_sequence=1,
       parent_operation_ids=["s-base"], kind="set_severity", payload={"value": "HIGH"})
_, view = request("GET", f"/plans/{plan}")
check("并发同值不产生冲突", view["severity"] == "HIGH" and view["field_conflicts"] == [], view)

# --- 4. 检查项合并：未被观察到的并发添加保留 ---
reset()
plan = new_plan("steps")
submit(plan, "t1", operation_id="add-1", actor_id="alice", actor_sequence=1,
       kind="add_step", payload={"step_id": "s1", "text": "断电"})
submit(plan, "t2", operation_id="add-2", actor_id="bob", actor_sequence=1,
       kind="add_step", payload={"step_id": "s2", "text": "疏散"})
submit(plan, "t3", operation_id="rm-1", actor_id="alice", actor_sequence=2,
       parent_operation_ids=["add-1"], kind="remove_step",
       payload={"step_id": "s1", "observed_add_operation_ids": ["add-1"]})
_, view = request("GET", f"/plans/{plan}")
check(
    "只删除观察到的添加项",
    [item["step_id"] for item in view["visible_steps"]] == ["s2"],
    view["visible_steps"],
)

status, unobserved = submit(
    plan, "t4", operation_id="rm-2", actor_id="carol", actor_sequence=1,
    kind="remove_step", payload={"step_id": "s2", "observed_add_operation_ids": []},
)
_, view = request("GET", f"/plans/{plan}")
check(
    "未观察到添加操作时不删除",
    [item["step_id"] for item in view["visible_steps"]] == ["s2"],
    view["visible_steps"],
)

status, reused = submit(
    plan, "t5", operation_id="add-3", actor_id="dave", actor_sequence=1,
    kind="add_step", payload={"step_id": "s1", "text": "复用"},
)
check("已删除的 step_id 不可复用", status == 409 and code(reused) == "STEP_ID_REUSED", reused)

# --- 5. 批量提交原子性 ---
reset()
plan = new_plan("batch")
status, batch = request(
    "POST",
    f"/plans/{plan}/operations/batch",
    {
        "idempotency_key": "b1",
        "operations": [
            {"operation_id": "b-2", "actor_id": "alice", "actor_sequence": 2,
             "kind": "add_step", "payload": {"step_id": "x2", "text": "第二"}},
            {"operation_id": "b-1", "actor_id": "alice", "actor_sequence": 1,
             "kind": "add_step", "payload": {"step_id": "x1", "text": "第一"}},
        ],
    },
)
_, view = request("GET", f"/plans/{plan}")
check(
    "批量乱序提交后全部接纳",
    status == 201
    and all(item["state"] == "ACCEPTED" for item in batch["operations"])
    and [item["step_id"] for item in view["visible_steps"]] == ["x1", "x2"],
    {"batch": batch, "view": view},
)

status, failed = request(
    "POST",
    f"/plans/{plan}/operations/batch",
    {
        "idempotency_key": "b2",
        "operations": [
            {"operation_id": "b-3", "actor_id": "bob", "actor_sequence": 1,
             "kind": "add_step", "payload": {"step_id": "x3", "text": "好的"}},
            {"operation_id": "b-4", "actor_id": "bob", "actor_sequence": 2,
             "kind": "add_step", "payload": {"step_id": "x1", "text": "重复"}},
        ],
    },
)
_, after = request("GET", f"/plans/{plan}/operations")
check(
    "批量失败时整批回滚",
    status == 409
    and code(failed) == "STEP_ID_REUSED"
    and [item["id"] for item in after["operations"]] == ["b-2", "b-1"],
    {"error": failed, "operations": [item["id"] for item in after["operations"]]},
)

# --- 6. 待定操作 20 分钟过期 ---
reset()
plan = new_plan("expiry")
submit(plan, "e1", operation_id="e-2", actor_id="alice", actor_sequence=2,
       kind="set_title", payload={"value": "孤儿"})
status, advanced = request("POST", "/clock/advance", {"minutes": 19})
_, still = request("GET", "/operations/e-2")
check("19 分钟仍待定", still["state"] == "PENDING", still)
status, advanced = request("POST", "/clock/advance", {"minutes": 1})
_, dead = request("GET", "/operations/e-2")
check(
    "20 分钟后过期",
    dead["state"] == "EXPIRED" and advanced["expired_operation_ids"] == ["e-2"],
    {"operation": dead, "advance": advanced},
)
status, revive = submit(
    plan, "e2", operation_id="e-1", actor_id="alice", actor_sequence=1,
    kind="set_title", payload={"value": "迟到的前驱"},
)
_, dead = request("GET", "/operations/e-2")
check("过期操作不可复活", dead["state"] == "EXPIRED", dead)

# --- 7. 快照审核、STALE 与发布回滚 ---
reset()
plan = new_plan("release", ["reviewer-a", "reviewer-b"])
submit(plan, "r1", operation_id="r-1", actor_id="alice", actor_sequence=1,
       kind="set_title", payload={"value": "V1"})
_, snapshot = request("POST", f"/plans/{plan}/snapshots", {"idempotency_key": "snap-1"})
status, partial = request(
    "POST", f"/snapshots/{snapshot['id']}/reviews",
    {"reviewer_id": "reviewer-a", "idempotency_key": "rev-1"},
)
_, pending_snapshot = request("GET", f"/snapshots/{snapshot['id']}")
check("部分审核仍待审", pending_snapshot["state"] == "PENDING_REVIEW", pending_snapshot)

status, early = request(
    "POST", f"/plans/{plan}/publish",
    {"snapshot_id": snapshot["id"], "idempotency_key": "pub-early"},
)
check(
    "未批准不能发布",
    status == 409 and code(early) == "SNAPSHOT_NOT_PUBLISHABLE",
    early,
)

request("POST", f"/snapshots/{snapshot['id']}/reviews",
        {"reviewer_id": "reviewer-b", "idempotency_key": "rev-2"})
_, approved = request("GET", f"/snapshots/{snapshot['id']}")
check("审核齐全后批准", approved["state"] == "APPROVED", approved)

status, release_one = request(
    "POST", f"/plans/{plan}/publish",
    {"snapshot_id": snapshot["id"], "release_epoch": 0, "idempotency_key": "pub-1"},
)
_, view = request("GET", f"/plans/{plan}")
check(
    "发布推进 epoch",
    status == 201
    and release_one["title"] == "V1"
    and view["release_epoch"] == 1
    and view["published_release_id"] == release_one["id"],
    {"release": release_one, "view": view},
)

status, stale_epoch = request(
    "POST", f"/plans/{plan}/publish",
    {"snapshot_id": snapshot["id"], "release_epoch": 0, "idempotency_key": "pub-2"},
)
check(
    "旧 epoch 被乐观锁拒绝",
    status == 409 and code(stale_epoch) == "RELEASE_EPOCH_CONFLICT",
    stale_epoch,
)

submit(plan, "r2", operation_id="r-2", actor_id="alice", actor_sequence=2,
       parent_operation_ids=["r-1"], kind="set_title", payload={"value": "V2"})
_, stale = request("GET", f"/snapshots/{snapshot['id']}")
check("新操作让快照 STALE", stale["state"] == "STALE", stale)

_, snapshot_two = request("POST", f"/plans/{plan}/snapshots", {"idempotency_key": "snap-2"})
request("POST", f"/snapshots/{snapshot_two['id']}/reviews",
        {"reviewer_id": "reviewer-a", "idempotency_key": "rev-3"})
request("POST", f"/snapshots/{snapshot_two['id']}/reviews",
        {"reviewer_id": "reviewer-b", "idempotency_key": "rev-4"})
_, release_two = request(
    "POST", f"/plans/{plan}/publish",
    {"snapshot_id": snapshot_two["id"], "release_epoch": 1, "idempotency_key": "pub-3"},
)
status, rolled = request(
    "POST", f"/plans/{plan}/rollback",
    {"release_id": release_one["id"], "release_epoch": 2, "idempotency_key": "roll-1"},
)
_, releases = request("GET", f"/plans/{plan}/releases")
check(
    "回滚生成新记录且不改历史",
    status == 201
    and rolled["title"] == "V1"
    and rolled["kind"] == "ROLLBACK"
    and rolled["source_release_id"] == release_one["id"]
    and [item["id"] for item in releases["releases"]]
    == [release_one["id"], release_two["id"], rolled["id"]]
    and releases["releases"][0]["title"] == "V1"
    and releases["releases"][1]["title"] == "V2",
    {"rolled": rolled, "releases": releases},
)

# --- 8. 快照 30 分钟过期 ---
reset()
plan = new_plan("snapshot-expiry")
_, snapshot = request("POST", f"/plans/{plan}/snapshots", {"idempotency_key": "snap-x"})
status, advanced = request("POST", "/clock/advance", {"minutes": 30})
_, expired = request("GET", f"/snapshots/{snapshot['id']}")
check(
    "快照 30 分钟未审完过期",
    expired["state"] == "EXPIRED" and advanced["expired_snapshot_ids"] == [snapshot["id"]],
    {"snapshot": expired, "advance": advanced},
)
status, late = request(
    "POST", f"/snapshots/{snapshot['id']}/reviews",
    {"reviewer_id": "reviewer-a", "idempotency_key": "rev-late"},
)
check(
    "过期快照不可再审",
    status == 409 and code(late) == "SNAPSHOT_NOT_REVIEWABLE",
    late,
)

# --- 9. 幂等 ---
reset()
plan = new_plan("idem")
status_one, one = submit(
    plan, "same", operation_id="i-1", actor_id="alice", actor_sequence=1,
    kind="set_title", payload={"value": "一次"},
)
status_two, two = submit(
    plan, "same", operation_id="i-1", actor_id="alice", actor_sequence=1,
    kind="set_title", payload={"value": "一次"},
)
check(
    "重放幂等键返回同一结果",
    status_one == 201 and status_two == 200 and one == two,
    {"first": one, "second": two},
)
status, mismatch = submit(
    plan, "same", operation_id="i-2", actor_id="alice", actor_sequence=2,
    kind="set_title", payload={"value": "两次"},
)
check(
    "幂等键换内容报冲突",
    status == 409 and code(mismatch) == "IDEMPOTENCY_KEY_REUSED",
    mismatch,
)
_, operations = request("GET", f"/plans/{plan}/operations")
check("重放不产生新操作", len(operations["operations"]) == 1, operations)

# --- 10. 审计 ---
_, audit = request("GET", f"/audit?plan_id={plan}")
types = [event["type"] for event in audit["events"]]
check(
    "审计记录关键事件",
    types == ["PLAN_CREATED", "OPERATION_RECEIVED", "OPERATION_ACCEPTED"],
    types,
)

print(f"\n结果：{PASSED}/{TOTAL}")
raise SystemExit(0 if PASSED == TOTAL else 1)
