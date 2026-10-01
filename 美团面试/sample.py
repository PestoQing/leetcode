#!/usr/bin/env python3

"""
默认样例仅验证服务连通性,部分契约的约定实现方式,不做业务层面校验测试
样例全部通过,不代表任何用例通过效果
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from typing import Any


BASE_URL = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"


def request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    raw = None if payload is None else json.dumps(payload).encode("utf-8")
    outgoing = urllib.request.Request(
        BASE_URL + path,
        data=raw,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(outgoing, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def check(name: str, condition: bool, detail: object) -> bool:
    if condition:
        print(f"[PASS] {name}")
        return True
    print(f"[FAIL] {name}: {detail}")
    return False


def main() -> int:
    passed = 0
    total = 0

    status, health = request("GET", "/health")
    total += 1
    passed += check("服务探活", status == 200 and health.get("status") == "ok", health)

    status, reset = request("POST", "/admin/reset", {})
    total += 1
    passed += check(
        "全量重置", status == 200 and reset == {"status": "ok", "now": 0}, reset
    )

    create_payload = {
        "name": "现场处置预案",
        "required_reviewer_ids": ["reviewer-a"],
        "idempotency_key": "sample-plan",
    }
    status, created = request("POST", "/plans", create_payload)
    total += 1
    passed += check(
        "创建测试状态",
        status == 201 and created.get("id") == "plan_1",
        created,
    )

    status, snapshot = request(
        "POST", "/plans/plan_1/snapshots", {"idempotency_key": "sample-snapshot"}
    )
    total += 1
    passed += check(
        "创建关联快照",
        status == 201 and snapshot.get("id") == "snapshot_1",
        snapshot,
    )

    status, review = request(
        "POST",
        "/snapshots/snapshot_1/reviews",
        {"reviewer_id": "reviewer-a", "idempotency_key": "sample-review"},
    )
    total += 1
    passed += check(
        "创建快照审核",
        status == 201 and review.get("id") == "review_1",
        review,
    )

    status, filtered_audit = request("GET", "/audit?plan_id=plan_1")
    total += 1
    passed += check(
        "按预案过滤审计",
        status == 200 and isinstance(filtered_audit.get("events"), list),
        filtered_audit,
    )

    status, advanced = request("POST", "/clock/advance", {"minutes": 7})
    total += 1
    passed += check("推进虚拟时钟", status == 200 and advanced.get("now") == 7, advanced)

    status, invalid_reset = request("POST", "/admin/reset", {"unexpected": True})
    _, retained_plan = request("GET", "/plans/plan_1")
    _, retained_snapshot = request("GET", "/snapshots/snapshot_1")
    _, retained_reviews = request("GET", "/snapshots/snapshot_1/reviews")
    _, retained_clock = request("GET", "/clock")
    total += 1
    passed += check(
        "非法重置不改变状态",
        status == 400
        and invalid_reset.get("error", {}).get("code") == "VALIDATION_ERROR"
        and retained_plan.get("id") == "plan_1"
        and retained_snapshot.get("id") == "snapshot_1"
        and retained_reviews.get("reviews", [{}])[0].get("id") == "review_1"
        and retained_clock == {"now": 7},
        {
            "reset": invalid_reset,
            "plan": retained_plan,
            "snapshot": retained_snapshot,
            "reviews": retained_reviews,
            "clock": retained_clock,
        },
    )

    status, reset = request("POST", "/admin/reset", {})
    total += 1
    passed += check(
        "重置业务状态", status == 200 and reset == {"status": "ok", "now": 0}, reset
    )

    status, plans = request("GET", "/plans")
    _, clock = request("GET", "/clock")
    snapshot_status, removed_snapshot = request("GET", "/snapshots/snapshot_1")
    reviews_status, removed_reviews = request("GET", "/snapshots/snapshot_1/reviews")
    total += 1
    passed += check(
        "重置清空对象与时钟",
        status == 200
        and plans == {"plans": []}
        and clock == {"now": 0}
        and snapshot_status == 404
        and reviews_status == 404,
        {
            "plans": plans,
            "clock": clock,
            "snapshot": removed_snapshot,
            "reviews": removed_reviews,
        },
    )

    status, audit = request("GET", "/audit")
    total += 1
    passed += check("空审计列表", status == 200 and audit == {"events": []}, audit)

    status, recreated = request("POST", "/plans", create_payload)
    total += 1
    passed += check(
        "重置计数器与幂等记录",
        status == 201 and recreated.get("id") == "plan_1",
        recreated,
    )

    status, repeat_reset = request("POST", "/admin/reset", {})
    total += 1
    passed += check(
        "重复重置幂等",
        status == 200 and repeat_reset == {"status": "ok", "now": 0},
        repeat_reset,
    )

    request("POST", "/plans", create_payload)
    concurrent_results: list[tuple[int, dict[str, Any]]] = []
    result_lock = threading.Lock()

    def concurrent_reset() -> None:
        result = request("POST", "/admin/reset", {})
        with result_lock:
            concurrent_results.append(result)

    workers = [threading.Thread(target=concurrent_reset) for _ in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    _, plans_after_concurrency = request("GET", "/plans")
    _, audit_after_concurrency = request("GET", "/audit")
    _, clock_after_concurrency = request("GET", "/clock")
    total += 1
    passed += check(
        "并发重置串行化",
        len(concurrent_results) == 4
        and all(item == (200, {"status": "ok", "now": 0}) for item in concurrent_results)
        and plans_after_concurrency == {"plans": []}
        and audit_after_concurrency == {"events": []}
        and clock_after_concurrency == {"now": 0},
        {
            "resets": concurrent_results,
            "plans": plans_after_concurrency,
            "audit": audit_after_concurrency,
            "clock": clock_after_concurrency,
        },
    )

    print(f"结果：{passed}/{total}")
    print("默认样例仅验证服务连通性,部分契约的约定实现方式,不做业务层面校验测试")
    print("样例全部通过,不代表任何用例通过效果")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
