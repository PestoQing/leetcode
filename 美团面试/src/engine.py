"""因果依赖推导、过期处理与物化视图计算。

这里的函数都只读写 PlanService 持有的字典，不做任何入参校验，
校验在 validation_support 里已经完成。
"""

from __future__ import annotations

from typing import Any

from src.validation_support import (
    DEFAULT_SEVERITY,
    OPERATION_TTL,
    SCALAR_KINDS,
    SNAPSHOT_TTL,
)


Record = dict[str, Any]

PENDING = "PENDING"
ACCEPTED = "ACCEPTED"
EXPIRED = "EXPIRED"


def plan_operations(service: Any, plan: Record) -> list[Record]:
    return [service.operations[identifier] for identifier in plan["operation_ids"]]


def accepted_operations(service: Any, plan: Record) -> list[Record]:
    return [item for item in plan_operations(service, plan) if item["state"] == ACCEPTED]


def pending_operation_ids(service: Any, plan: Record) -> list[str]:
    return sorted(
        item["id"] for item in plan_operations(service, plan) if item["state"] == PENDING
    )


def actor_predecessor(service: Any, operation: Record) -> Record | None:
    """隐式因果：同一成员在同一预案内，actor_sequence 的前一条。"""
    if operation["actor_sequence"] <= 1:
        return None
    target = operation["actor_sequence"] - 1
    plan = service.plans.get(operation["plan_id"])
    if plan is None:
        return None
    for candidate in plan_operations(service, plan):
        if (
            candidate["actor_id"] == operation["actor_id"]
            and candidate["actor_sequence"] == target
        ):
            return candidate
    return None


def actor_sibling(service: Any, plan: Record, actor_id: str, sequence: int) -> Record | None:
    for candidate in plan_operations(service, plan):
        if candidate["actor_id"] == actor_id and candidate["actor_sequence"] == sequence:
            return candidate
    return None


def dependency_ids(service: Any, operation: Record) -> list[str]:
    identifiers = list(operation["parent_operation_ids"])
    predecessor = actor_predecessor(service, operation)
    if predecessor is not None:
        identifiers.append(predecessor["id"])
    return identifiers


def is_acceptable(service: Any, operation: Record) -> bool:
    """显式父操作与隐式前驱全部 ACCEPTED 时才可接纳。"""
    for parent_id in operation["parent_operation_ids"]:
        parent = service.operations.get(parent_id)
        if parent is None or parent["state"] != ACCEPTED:
            return False
    if operation["actor_sequence"] > 1:
        predecessor = actor_predecessor(service, operation)
        if predecessor is None or predecessor["state"] != ACCEPTED:
            return False
    return True


def settle_plan(service: Any, plan: Record) -> list[str]:
    """反复扫描待定操作，直到没有新的操作可被接纳；返回本次接纳的 ID。"""
    accepted: list[str] = []
    progressed = True
    while progressed:
        progressed = False
        for operation in plan_operations(service, plan):
            if operation["state"] != PENDING or not is_acceptable(service, operation):
                continue
            operation["state"] = ACCEPTED
            operation["accepted_at"] = service.clock.now
            operation["accept_order"] = service.next_accept_order()
            accepted.append(operation["id"])
            progressed = True
    if accepted:
        plan["updated_at"] = service.clock.now
    return accepted


def head_operation_ids(service: Any, plan: Record) -> list[str]:
    """头部 = 没有被任何其它已接纳操作依赖的已接纳操作。"""
    accepted = accepted_operations(service, plan)
    covered: set[str] = set()
    for operation in accepted:
        covered.update(dependency_ids(service, operation))
    return sorted(item["id"] for item in accepted if item["id"] not in covered)


def ancestor_map(service: Any, plan: Record) -> dict[str, set[str]]:
    """每条已接纳操作的祖先集合；accept_order 升序即拓扑序。"""
    ordered = sorted(accepted_operations(service, plan), key=lambda item: item["accept_order"])
    known = {item["id"] for item in ordered}
    ancestors: dict[str, set[str]] = {}
    for operation in ordered:
        collected: set[str] = set()
        for dependency in dependency_ids(service, operation):
            if dependency in known:
                collected.add(dependency)
                collected.update(ancestors.get(dependency, set()))
        ancestors[operation["id"]] = collected
    return ancestors


def concurrent_frontier(
    operations: list[Record], ancestors: dict[str, set[str]]
) -> list[Record]:
    """剔除被同类操作因果覆盖的旧值，剩下的就是互相并发的最新值。"""
    identifiers = {item["id"] for item in operations}
    return [
        item
        for item in operations
        if not any(
            item["id"] in ancestors.get(other, set())
            for other in identifiers
            if other != item["id"]
        )
    ]


def scalar_field(
    service: Any,
    plan: Record,
    ancestors: dict[str, set[str]],
    kind: str,
    default: Any,
) -> tuple[Any, Record | None]:
    candidates = [item for item in accepted_operations(service, plan) if item["kind"] == kind]
    if not candidates:
        return default, None
    frontier = concurrent_frontier(candidates, ancestors)
    values = sorted({item["payload"]["value"] for item in frontier})
    if len(values) == 1:
        return values[0], None
    conflict = {
        "field": SCALAR_KINDS[kind],
        "operation_ids": sorted(item["id"] for item in frontier),
        "values": values,
    }
    return None, conflict


def visible_steps(service: Any, plan: Record) -> list[Record]:
    """remove_step 只注销它观察到的那些 add_step；未被观察的并发添加保留。"""
    accepted = accepted_operations(service, plan)
    additions = [item for item in accepted if item["kind"] == "add_step"]
    removals = [item for item in accepted if item["kind"] == "remove_step"]
    retired: set[str] = set()
    for removal in removals:
        observed = set(removal["payload"]["observed_add_operation_ids"])
        for addition in additions:
            if (
                addition["id"] in observed
                and addition["payload"]["step_id"] == removal["payload"]["step_id"]
            ):
                retired.add(addition["id"])
    survivors = sorted(
        (item for item in additions if item["id"] not in retired),
        key=lambda item: (item["accept_order"], item["id"]),
    )
    grouped: dict[str, Record] = {}
    for addition in survivors:
        grouped.setdefault(addition["payload"]["step_id"], addition)
    return [
        {
            "step_id": step_id,
            "text": addition["payload"]["text"],
            "add_operation_id": addition["id"],
        }
        for step_id, addition in sorted(grouped.items())
    ]


def claimed_step_ids(service: Any, plan: Record) -> set[str]:
    """已被占用的 step_id：含待定操作，含已删除的墓碑，不含已过期操作。"""
    claimed: set[str] = set()
    for operation in plan_operations(service, plan):
        if operation["state"] == EXPIRED:
            continue
        if operation["kind"] in ("add_step", "remove_step"):
            claimed.add(operation["payload"]["step_id"])
    return claimed


def materialize(service: Any, plan: Record) -> Record:
    """物化视图：标量字段冲突检测 + 检查项合并。"""
    ancestors = ancestor_map(service, plan)
    conflicts: list[Record] = []
    title, title_conflict = scalar_field(
        service, plan, ancestors, "set_title", plan["name"]
    )
    if title_conflict is not None:
        conflicts.append(title_conflict)
    severity, severity_conflict = scalar_field(
        service, plan, ancestors, "set_severity", DEFAULT_SEVERITY
    )
    if severity_conflict is not None:
        conflicts.append(severity_conflict)
    return {
        "title": title,
        "severity": severity,
        "visible_steps": visible_steps(service, plan),
        "field_conflicts": sorted(conflicts, key=lambda item: item["field"]),
        "head_operation_ids": head_operation_ids(service, plan),
        "pending_operation_ids": pending_operation_ids(service, plan),
    }


def expire_operations(service: Any) -> list[str]:
    """PENDING 超过 20 分钟即 EXPIRED，不可复活。"""
    now = service.clock.now
    expired: list[str] = []
    for operation in service.operations.values():
        if operation["state"] == PENDING and now >= operation["expires_at"]:
            operation["state"] = EXPIRED
            expired.append(operation["id"])
    return sorted(expired)


def expire_snapshots(service: Any) -> list[str]:
    """未在 30 分钟内审完的快照标记过期；已批准的不再过期。"""
    now = service.clock.now
    expired: list[str] = []
    for snapshot in service.snapshots.values():
        if snapshot["approved_at"] is not None or snapshot["expired_at"] is not None:
            continue
        if now >= snapshot["review_deadline_at"]:
            snapshot["expired_at"] = now
            expired.append(snapshot["id"])
    return sorted(expired)


def snapshot_state(service: Any, snapshot: Record) -> str:
    plan = service.plans.get(snapshot["plan_id"])
    if plan is not None and snapshot["head_operation_ids"] != head_operation_ids(service, plan):
        return "STALE"
    if snapshot["expired_at"] is not None:
        return "EXPIRED"
    if snapshot["approved_at"] is not None:
        return "APPROVED"
    return "PENDING_REVIEW"


def operation_deadline(service: Any) -> int:
    return service.clock.now + OPERATION_TTL


def snapshot_deadline(service: Any) -> int:
    return service.clock.now + SNAPSHOT_TTL
