"""请求体校验：把 HTTP 入参翻译成领域对象，失败一律抛 ApiError。"""

from __future__ import annotations

from typing import Any

from domain import ApiError, FieldReader, JsonObject, JsonShape


SEVERITY_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
DEFAULT_SEVERITY = "MEDIUM"
OPERATION_KINDS = ("set_title", "set_severity", "add_step", "remove_step")
SCALAR_KINDS = {"set_title": "title", "set_severity": "severity"}
OPERATION_TTL = 20
SNAPSHOT_TTL = 30
MAX_BATCH_SIZE = 64


def parse_port(raw: Any) -> int:
    """解析 PORT 环境变量，非法值直接让进程起不来而不是静默降级。"""
    try:
        port = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"PORT is not an integer: {raw!r}") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"PORT is out of range: {port}")
    return port


def parse_plan_request(body: Any) -> tuple[JsonObject, str]:
    fields = FieldReader(body)
    name = fields.text("name", 1, 80)
    reviewers = fields.text_list(
        "required_reviewer_ids",
        minimum=1,
        maximum=8,
        unique=True,
        sorted_output=True,
    )
    key = fields.text("idempotency_key", 1, 128)
    fields.finish()
    return {"name": name, "required_reviewer_ids": reviewers}, key


def parse_operation_payload(kind: str, payload: Any) -> JsonObject:
    fields = FieldReader(payload, "payload")
    if kind == "set_title":
        value = fields.text("value", 1, 120)
        fields.finish()
        return {"value": value}
    if kind == "set_severity":
        value = fields.one_of("value", SEVERITY_LEVELS)
        fields.finish()
        return {"value": value}
    if kind == "add_step":
        step_id = fields.identifier("step_id")
        text = fields.text("text", 1, 200)
        fields.finish()
        return {"step_id": step_id, "text": text}
    step_id = fields.identifier("step_id")
    observed = fields.optional_text_list(
        "observed_add_operation_ids",
        minimum=0,
        maximum=64,
        unique=True,
        sorted_output=True,
        identifiers=True,
    )
    fields.finish()
    return {"step_id": step_id, "observed_add_operation_ids": observed or []}


def parse_operation_fields(body: Any, field: str = "request body") -> JsonObject:
    """解析一条操作，不含 idempotency_key（批量提交时整批共用一个键）。"""
    fields = FieldReader(body, field)
    operation_id = fields.identifier("operation_id")
    actor_id = fields.text("actor_id", 1, 64)
    sequence = fields.integer("actor_sequence", 1, 1_000_000)
    parents = fields.optional_text_list(
        "parent_operation_ids",
        minimum=0,
        maximum=16,
        unique=True,
        sorted_output=True,
        identifiers=True,
    )
    kind = fields.one_of("kind", OPERATION_KINDS)
    payload = parse_operation_payload(kind, fields.object("payload"))
    fields.finish()
    parents = parents or []
    if operation_id in parents:
        raise ApiError(f"{field}: operation cannot depend on itself")
    return {
        "operation_id": operation_id,
        "actor_id": actor_id,
        "actor_sequence": sequence,
        "parent_operation_ids": parents,
        "kind": kind,
        "payload": payload,
    }


def parse_operation_request(body: Any) -> tuple[JsonObject, str]:
    values = JsonShape.object(body)
    if "idempotency_key" not in values:
        raise ApiError("idempotency_key is required")
    key = JsonShape.text(values["idempotency_key"], "idempotency_key", 1, 128)
    rest = {name: value for name, value in values.items() if name != "idempotency_key"}
    return parse_operation_fields(rest), key


def parse_batch_request(body: Any) -> tuple[list[JsonObject], str]:
    fields = FieldReader(body)
    raw_items = JsonShape.object_list(
        fields.required_raw("operations"), "operations", minimum=1, maximum=MAX_BATCH_SIZE
    )
    key = fields.text("idempotency_key", 1, 128)
    fields.finish()
    drafts = [
        parse_operation_fields(item, f"operations[{index}]")
        for index, item in enumerate(raw_items)
    ]
    identifiers = [draft["operation_id"] for draft in drafts]
    if len(identifiers) != len(set(identifiers)):
        raise ApiError("operations contains duplicate operation_id")
    return drafts, key


def parse_key_only_request(body: Any) -> str:
    fields = FieldReader(body)
    key = fields.text("idempotency_key", 1, 128)
    fields.finish()
    return key


def parse_review_request(body: Any) -> tuple[str, str]:
    fields = FieldReader(body)
    reviewer_id = fields.text("reviewer_id", 1, 64)
    key = fields.text("idempotency_key", 1, 128)
    fields.finish()
    return reviewer_id, key


def parse_publish_request(body: Any) -> tuple[str, int | None, str]:
    fields = FieldReader(body)
    snapshot_id = fields.text("snapshot_id", 1, 256)
    epoch = fields.optional_integer("release_epoch", 0)
    key = fields.text("idempotency_key", 1, 128)
    fields.finish()
    return snapshot_id, epoch, key


def parse_rollback_request(body: Any) -> tuple[str, int | None, str]:
    fields = FieldReader(body)
    release_id = fields.text("release_id", 1, 256)
    epoch = fields.optional_integer("release_epoch", 0)
    key = fields.text("idempotency_key", 1, 128)
    fields.finish()
    return release_id, epoch, key


def parse_advance_request(body: Any) -> tuple[int, str | None]:
    fields = FieldReader(body)
    minutes = fields.integer("minutes", 1, 10_000)
    key = fields.optional_text("idempotency_key", 1, 128)
    fields.finish()
    return minutes, key
