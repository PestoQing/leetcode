"""全量重置：清空所有业务对象、审计、幂等记录、ID 计数器与虚拟时钟。"""

from __future__ import annotations

from typing import Any

from domain import JsonObject


def reset_service(service: Any) -> JsonObject:
    with service.lock:
        service.clock.reset()
        for sequence in service.sequences():
            sequence.reset()
        service.plans.clear()
        service.operations.clear()
        service.snapshots.clear()
        service.reviews.clear()
        service.releases.clear()
        service.events.clear()
        service.root_idempotency.clear()
        service.accept_counter = 0
        return {"status": "ok", "now": service.clock.now}
