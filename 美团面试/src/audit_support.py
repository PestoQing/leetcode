"""审计事件的写入与查询。"""

from __future__ import annotations

from typing import Any

from domain import JsonObject


EVENT_FIELDS = ("plan_id", "operation_id", "snapshot_id", "review_id", "release_id")


def record_event(service: Any, event_type: str, **references: str | None) -> JsonObject:
    event = {
        "id": service.event_ids.next(),
        "type": event_type,
        "at": service.clock.now,
    }
    for name in EVENT_FIELDS:
        event[name] = references.get(name)
    service.events.append(event)
    return event


def record_many(service: Any, event_type: str, plan_id: str, operation_ids: list[str]) -> None:
    for operation_id in operation_ids:
        record_event(service, event_type, plan_id=plan_id, operation_id=operation_id)


def list_events(service: Any, plan_id: str | None = None) -> list[JsonObject]:
    if plan_id is None:
        return [dict(event) for event in service.events]
    return [dict(event) for event in service.events if event["plan_id"] == plan_id]
