#!/usr/bin/env python3
from __future__ import annotations

import copy
import os
import threading
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterator

from src.audit_support import list_events, record_event, record_many
from src.engine import (
    PENDING,
    actor_sibling,
    expire_operations,
    expire_snapshots,
    materialize,
    observed_step_ids,
    operation_deadline,
    settle_plan,
    snapshot_deadline,
    snapshot_state,
)
from src.reset_support import reset_service
from src.validation_support import (
    parse_advance_request,
    parse_batch_request,
    parse_key_only_request,
    parse_operation_request,
    parse_plan_request,
    parse_port,
    parse_publish_request,
    parse_review_request,
    parse_rollback_request,
)
from domain import (
    ApiError,
    IdSequence,
    IdempotencyTable,
    JsonResponse,
    JsonShape,
    JsonWire,
    LogicalClock,
    RoutePath,
)


class PlanService:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.clock = LogicalClock()
        self.plan_ids = IdSequence("plan")
        self.snapshot_ids = IdSequence("snapshot")
        self.review_ids = IdSequence("review")
        self.release_ids = IdSequence("release")
        self.event_ids = IdSequence("event")
        self.plans: dict[str, dict[str, Any]] = {}
        self.operations: dict[str, dict[str, Any]] = {}
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.reviews: dict[str, dict[str, Any]] = {}
        self.releases: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.accept_counter = 0
        self.root_idempotency = IdempotencyTable()

    # ---------- 基础设施 ----------

    def sequences(self) -> tuple[IdSequence, ...]:
        return (
            self.plan_ids,
            self.snapshot_ids,
            self.review_ids,
            self.release_ids,
            self.event_ids,
        )

    def next_accept_order(self) -> int:
        self.accept_counter += 1
        return self.accept_counter

    def _capture(self) -> dict[str, Any]:
        return copy.deepcopy(
            {
                "clock": self.clock.snapshot(),
                "sequences": [sequence.current() for sequence in self.sequences()],
                "plans": self.plans,
                "operations": self.operations,
                "snapshots": self.snapshots,
                "reviews": self.reviews,
                "releases": self.releases,
                "events": self.events,
                "idempotency": self.root_idempotency.items,
                "accept_counter": self.accept_counter,
            }
        )

    def _restore(self, state: dict[str, Any]) -> None:
        self.clock.restore(state["clock"])
        for sequence, value in zip(self.sequences(), state["sequences"]):
            sequence.restore(value)
        self.plans = state["plans"]
        self.operations = state["operations"]
        self.snapshots = state["snapshots"]
        self.reviews = state["reviews"]
        self.releases = state["releases"]
        self.events = state["events"]
        self.root_idempotency.items = state["idempotency"]
        self.accept_counter = state["accept_counter"]

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        """任何异常都回滚到调用前的状态，失败请求不留部分写入。"""
        state = self._capture()
        try:
            yield
        except BaseException:
            self._restore(state)
            raise

    def _replay(self, key: str, request: dict[str, Any]) -> JsonResponse | None:
        stored = self.root_idempotency.lookup(key, request)
        return None if stored is None else JsonResponse.ok(stored)

    def reset(self) -> dict[str, Any]:
        return reset_service(self)

    def health(self) -> dict[str, Any]:
        with self.lock:
            return {"status": "ok"}

    def clock_view(self) -> dict[str, int]:
        with self.lock:
            return {"now": self.clock.now}

    # ---------- 实体查找 ----------

    def _require_plan(self, plan_id: str) -> dict[str, Any]:
        plan = self.plans.get(plan_id)
        if plan is None:
            raise ApiError(f"plan not found: {plan_id}", HTTPStatus.NOT_FOUND, "NOT_FOUND")
        return plan

    def _require_operation(self, operation_id: str) -> dict[str, Any]:
        operation = self.operations.get(operation_id)
        if operation is None:
            raise ApiError(
                f"operation not found: {operation_id}", HTTPStatus.NOT_FOUND, "NOT_FOUND"
            )
        return operation

    def _require_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        snapshot = self.snapshots.get(snapshot_id)
        if snapshot is None:
            raise ApiError(
                f"snapshot not found: {snapshot_id}", HTTPStatus.NOT_FOUND, "NOT_FOUND"
            )
        return snapshot

    def _require_release(self, release_id: str) -> dict[str, Any]:
        release = self.releases.get(release_id)
        if release is None:
            raise ApiError(
                f"release not found: {release_id}", HTTPStatus.CONFLICT, "RELEASE_NOT_FOUND"
            )
        return release

    # ---------- 视图 ----------

    def _plan_view(self, record: dict[str, Any]) -> dict[str, Any]:
        view = materialize(self, record)
        return {
            "id": record["id"],
            "name": record["name"],
            "required_reviewer_ids": list(record["required_reviewer_ids"]),
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
            "head_operation_ids": view["head_operation_ids"],
            "title": view["title"],
            "severity": view["severity"],
            "visible_steps": view["visible_steps"],
            "field_conflicts": view["field_conflicts"],
            "pending_operation_ids": view["pending_operation_ids"],
            "release_epoch": record["release_epoch"],
            "published_release_id": record["published_release_id"],
        }

    def _operation_view(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "plan_id": record["plan_id"],
            "actor_id": record["actor_id"],
            "actor_sequence": record["actor_sequence"],
            "parent_operation_ids": list(record["parent_operation_ids"]),
            "kind": record["kind"],
            "payload": JsonShape.public_object(record["payload"]),
            "state": record["state"],
            "created_at": record["created_at"],
            "accepted_at": record["accepted_at"],
            "expires_at": record["expires_at"],
        }

    def _snapshot_view(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "plan_id": record["plan_id"],
            "head_operation_ids": list(record["head_operation_ids"]),
            "title": record["title"],
            "severity": record["severity"],
            "visible_steps": JsonShape.clone(record["visible_steps"]),
            "state": snapshot_state(self, record),
            "reviewer_ids": sorted(record["reviewer_ids"]),
            "required_reviewer_ids": list(record["required_reviewer_ids"]),
            "created_at": record["created_at"],
            "review_deadline_at": record["review_deadline_at"],
        }

    def _review_view(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "snapshot_id": record["snapshot_id"],
            "reviewer_id": record["reviewer_id"],
            "created_at": record["created_at"],
        }

    def _release_view(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "plan_id": record["plan_id"],
            "snapshot_id": record["snapshot_id"],
            "kind": record["kind"],
            "source_release_id": record["source_release_id"],
            "release_epoch": record["release_epoch"],
            "title": record["title"],
            "severity": record["severity"],
            "visible_steps": JsonShape.clone(record["visible_steps"]),
            "created_at": record["created_at"],
        }

    # ---------- 预案 ----------

    def create_plan(self, body: Any) -> JsonResponse:
        with self.lock, self._transaction():
            draft, key = parse_plan_request(body)
            request = {"route": "POST /plans", **draft}
            replay = self._replay(key, request)
            if replay is not None:
                return replay
            now = self.clock.now
            plan_id = self.plan_ids.next()
            record = {
                "id": plan_id,
                "name": draft["name"],
                "required_reviewer_ids": draft["required_reviewer_ids"],
                "created_at": now,
                "updated_at": now,
                "operation_ids": [],
                "snapshot_ids": [],
                "release_ids": [],
                "release_epoch": 0,
                "published_release_id": None,
            }
            self.plans[plan_id] = record
            record_event(self, "PLAN_CREATED", plan_id=plan_id)
            response = self._plan_view(record)
            self.root_idempotency.save(key, request, response)
            return JsonResponse.created(response)

    def list_plans(self) -> dict[str, Any]:
        with self.lock:
            return {"plans": [self._plan_view(record) for record in self.plans.values()]}

    def get_plan(self, plan_id: str) -> dict[str, Any]:
        with self.lock:
            return self._plan_view(self._require_plan(plan_id))

    # ---------- 操作 ----------

    def _admit_operation(
        self, plan: dict[str, Any], draft: dict[str, Any]
    ) -> dict[str, Any]:
        operation_id = draft["operation_id"]
        if operation_id in self.operations:
            raise ApiError(
                f"operation_id already exists: {operation_id}",
                HTTPStatus.CONFLICT,
                "OPERATION_ID_REUSED",
            )
        if actor_sibling(self, plan, draft["actor_id"], draft["actor_sequence"]) is not None:
            raise ApiError(
                "actor_sequence already used by this actor in the plan",
                HTTPStatus.CONFLICT,
                "ACTOR_SEQUENCE_REUSED",
            )
        for parent_id in draft["parent_operation_ids"]:
            parent = self.operations.get(parent_id)
            if parent is not None and parent["plan_id"] != plan["id"]:
                raise ApiError(
                    "parent operation belongs to another plan",
                    HTTPStatus.CONFLICT,
                    "PARENT_PLAN_MISMATCH",
                )
        if (
            draft["kind"] == "add_step"
            and draft["payload"]["step_id"] in observed_step_ids(self, plan, draft)
        ):
            raise ApiError(
                "step_id was already added or retired in this causal history",
                HTTPStatus.CONFLICT,
                "STEP_ID_REUSED",
            )
        now = self.clock.now
        record = {
            "id": operation_id,
            "plan_id": plan["id"],
            "actor_id": draft["actor_id"],
            "actor_sequence": draft["actor_sequence"],
            "parent_operation_ids": list(draft["parent_operation_ids"]),
            "kind": draft["kind"],
            "payload": JsonShape.public_object(draft["payload"]),
            "state": PENDING,
            "created_at": now,
            "accepted_at": None,
            "expires_at": operation_deadline(self),
            "accept_order": 0,
        }
        self.operations[operation_id] = record
        plan["operation_ids"].append(operation_id)
        record_event(
            self, "OPERATION_RECEIVED", plan_id=plan["id"], operation_id=operation_id
        )
        return record

    def create_operation(self, plan_id: str, body: Any) -> JsonResponse:
        with self.lock, self._transaction():
            plan = self._require_plan(plan_id)
            draft, key = parse_operation_request(body)
            request = {"route": f"POST /plans/{plan_id}/operations", **draft}
            replay = self._replay(key, request)
            if replay is not None:
                return replay
            record = self._admit_operation(plan, draft)
            record_many(self, "OPERATION_ACCEPTED", plan_id, settle_plan(self, plan))
            response = self._operation_view(self.operations[record["id"]])
            self.root_idempotency.save(key, request, response)
            return JsonResponse.created(response)

    def create_operation_batch(self, plan_id: str, body: Any) -> JsonResponse:
        with self.lock, self._transaction():
            plan = self._require_plan(plan_id)
            drafts, key = parse_batch_request(body)
            request = {
                "route": f"POST /plans/{plan_id}/operations/batch",
                "operations": drafts,
            }
            replay = self._replay(key, request)
            if replay is not None:
                return replay
            created = [self._admit_operation(plan, draft)["id"] for draft in drafts]
            record_many(self, "OPERATION_ACCEPTED", plan_id, settle_plan(self, plan))
            response = {
                "operations": [
                    self._operation_view(self.operations[identifier])
                    for identifier in created
                ]
            }
            self.root_idempotency.save(key, request, response)
            return JsonResponse.created(response)

    def list_operations(self, plan_id: str) -> dict[str, Any]:
        with self.lock:
            plan = self._require_plan(plan_id)
            return {
                "operations": [
                    self._operation_view(self.operations[identifier])
                    for identifier in plan["operation_ids"]
                ]
            }

    def get_operation(self, operation_id: str) -> dict[str, Any]:
        with self.lock:
            return self._operation_view(self._require_operation(operation_id))

    # ---------- 快照与审核 ----------

    def create_snapshot(self, plan_id: str, body: Any) -> JsonResponse:
        with self.lock, self._transaction():
            plan = self._require_plan(plan_id)
            key = parse_key_only_request(body)
            request = {"route": f"POST /plans/{plan_id}/snapshots"}
            replay = self._replay(key, request)
            if replay is not None:
                return replay
            view = materialize(self, plan)
            if view["pending_operation_ids"] or view["field_conflicts"]:
                raise ApiError(
                    "plan has pending operations or unresolved field conflicts",
                    HTTPStatus.CONFLICT,
                    "PLAN_NOT_SNAPSHOTTABLE",
                )
            now = self.clock.now
            snapshot_id = self.snapshot_ids.next()
            record = {
                "id": snapshot_id,
                "plan_id": plan_id,
                "head_operation_ids": view["head_operation_ids"],
                "title": view["title"],
                "severity": view["severity"],
                "visible_steps": view["visible_steps"],
                "required_reviewer_ids": list(plan["required_reviewer_ids"]),
                "reviewer_ids": [],
                "review_ids": [],
                "created_at": now,
                "review_deadline_at": snapshot_deadline(self),
                "approved_at": None,
                "expired_at": None,
            }
            self.snapshots[snapshot_id] = record
            plan["snapshot_ids"].append(snapshot_id)
            record_event(
                self, "SNAPSHOT_CREATED", plan_id=plan_id, snapshot_id=snapshot_id
            )
            response = self._snapshot_view(record)
            self.root_idempotency.save(key, request, response)
            return JsonResponse.created(response)

    def list_snapshots(self, plan_id: str) -> dict[str, Any]:
        with self.lock:
            plan = self._require_plan(plan_id)
            return {
                "snapshots": [
                    self._snapshot_view(self.snapshots[identifier])
                    for identifier in plan["snapshot_ids"]
                ]
            }

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        with self.lock:
            return self._snapshot_view(self._require_snapshot(snapshot_id))

    def create_review(self, snapshot_id: str, body: Any) -> JsonResponse:
        with self.lock, self._transaction():
            snapshot = self._require_snapshot(snapshot_id)
            reviewer_id, key = parse_review_request(body)
            request = {
                "route": f"POST /snapshots/{snapshot_id}/reviews",
                "reviewer_id": reviewer_id,
            }
            replay = self._replay(key, request)
            if replay is not None:
                return replay
            if snapshot_state(self, snapshot) in ("STALE", "EXPIRED"):
                raise ApiError(
                    "snapshot is not reviewable in the current state",
                    HTTPStatus.CONFLICT,
                    "SNAPSHOT_NOT_REVIEWABLE",
                )
            if reviewer_id not in snapshot["required_reviewer_ids"]:
                raise ApiError(
                    f"reviewer is not required for this snapshot: {reviewer_id}",
                    HTTPStatus.CONFLICT,
                    "REVIEWER_NOT_REQUIRED",
                )
            if reviewer_id in snapshot["reviewer_ids"]:
                raise ApiError(
                    f"reviewer already reviewed this snapshot: {reviewer_id}",
                    HTTPStatus.CONFLICT,
                    "REVIEW_ALREADY_EXISTS",
                )
            now = self.clock.now
            review_id = self.review_ids.next()
            record = {
                "id": review_id,
                "snapshot_id": snapshot_id,
                "reviewer_id": reviewer_id,
                "created_at": now,
            }
            self.reviews[review_id] = record
            snapshot["reviewer_ids"].append(reviewer_id)
            snapshot["review_ids"].append(review_id)
            if set(snapshot["required_reviewer_ids"]) <= set(snapshot["reviewer_ids"]):
                snapshot["approved_at"] = now
            record_event(
                self,
                "SNAPSHOT_REVIEWED",
                plan_id=snapshot["plan_id"],
                snapshot_id=snapshot_id,
                review_id=review_id,
            )
            response = self._review_view(record)
            self.root_idempotency.save(key, request, response)
            return JsonResponse.created(response)

    def list_reviews(self, snapshot_id: str) -> dict[str, Any]:
        with self.lock:
            snapshot = self._require_snapshot(snapshot_id)
            return {
                "reviews": [
                    self._review_view(self.reviews[identifier])
                    for identifier in snapshot["review_ids"]
                ]
            }

    # ---------- 发布与回滚 ----------

    def _check_epoch(self, plan: dict[str, Any], epoch: int | None) -> None:
        if epoch is not None and epoch != plan["release_epoch"]:
            raise ApiError(
                f"release_epoch is stale: expected {plan['release_epoch']}",
                HTTPStatus.CONFLICT,
                "RELEASE_EPOCH_CONFLICT",
            )

    def _append_release(
        self,
        plan: dict[str, Any],
        source: dict[str, Any],
        kind: str,
        source_release_id: str | None,
    ) -> dict[str, Any]:
        plan["release_epoch"] += 1
        release_id = self.release_ids.next()
        record = {
            "id": release_id,
            "plan_id": plan["id"],
            "snapshot_id": source["snapshot_id"] if "snapshot_id" in source else source["id"],
            "kind": kind,
            "source_release_id": source_release_id,
            "release_epoch": plan["release_epoch"],
            "title": source["title"],
            "severity": source["severity"],
            "visible_steps": JsonShape.clone(source["visible_steps"]),
            "created_at": self.clock.now,
        }
        self.releases[release_id] = record
        plan["release_ids"].append(release_id)
        plan["published_release_id"] = release_id
        plan["updated_at"] = self.clock.now
        return record

    def publish(self, plan_id: str, body: Any) -> JsonResponse:
        with self.lock, self._transaction():
            plan = self._require_plan(plan_id)
            snapshot_id, epoch, key = parse_publish_request(body)
            request = {
                "route": f"POST /plans/{plan_id}/publish",
                "snapshot_id": snapshot_id,
                "release_epoch": epoch,
            }
            replay = self._replay(key, request)
            if replay is not None:
                return replay
            snapshot = self._require_snapshot(snapshot_id)
            if snapshot["plan_id"] != plan_id:
                raise ApiError(
                    "snapshot belongs to another plan",
                    HTTPStatus.CONFLICT,
                    "SNAPSHOT_PLAN_MISMATCH",
                )
            self._check_epoch(plan, epoch)
            if snapshot_state(self, snapshot) != "APPROVED":
                raise ApiError(
                    "snapshot is not publishable in the current state",
                    HTTPStatus.CONFLICT,
                    "SNAPSHOT_NOT_PUBLISHABLE",
                )
            record = self._append_release(plan, snapshot, "PUBLISH", None)
            record_event(
                self,
                "RELEASE_PUBLISHED",
                plan_id=plan_id,
                snapshot_id=snapshot_id,
                release_id=record["id"],
            )
            response = self._release_view(record)
            self.root_idempotency.save(key, request, response)
            return JsonResponse.created(response)

    def rollback(self, plan_id: str, body: Any) -> JsonResponse:
        with self.lock, self._transaction():
            plan = self._require_plan(plan_id)
            release_id, epoch, key = parse_rollback_request(body)
            request = {
                "route": f"POST /plans/{plan_id}/rollback",
                "release_id": release_id,
                "release_epoch": epoch,
            }
            replay = self._replay(key, request)
            if replay is not None:
                return replay
            source = self._require_release(release_id)
            if source["plan_id"] != plan_id:
                raise ApiError(
                    "release belongs to another plan",
                    HTTPStatus.CONFLICT,
                    "RELEASE_NOT_FOUND",
                )
            self._check_epoch(plan, epoch)
            record = self._append_release(plan, source, "ROLLBACK", release_id)
            record_event(
                self,
                "RELEASE_ROLLED_BACK",
                plan_id=plan_id,
                snapshot_id=record["snapshot_id"],
                release_id=record["id"],
            )
            response = self._release_view(record)
            self.root_idempotency.save(key, request, response)
            return JsonResponse.created(response)

    def list_releases(self, plan_id: str) -> dict[str, Any]:
        with self.lock:
            plan = self._require_plan(plan_id)
            return {
                "releases": [
                    self._release_view(self.releases[identifier])
                    for identifier in plan["release_ids"]
                ]
            }

    # ---------- 时钟与审计 ----------

    def advance_clock(self, body: Any) -> JsonResponse:
        with self.lock, self._transaction():
            minutes, key = parse_advance_request(body)
            request = {"route": "POST /clock/advance", "minutes": minutes}
            if key is not None:
                replay = self._replay(key, request)
                if replay is not None:
                    return replay
            self.clock.advance(minutes)
            expired_operations = expire_operations(self)
            for identifier in expired_operations:
                record_event(
                    self,
                    "OPERATION_EXPIRED",
                    plan_id=self.operations[identifier]["plan_id"],
                    operation_id=identifier,
                )
            expired_snapshots = expire_snapshots(self)
            for identifier in expired_snapshots:
                record_event(
                    self,
                    "SNAPSHOT_EXPIRED",
                    plan_id=self.snapshots[identifier]["plan_id"],
                    snapshot_id=identifier,
                )
            response = {
                "now": self.clock.now,
                "expired_operation_ids": expired_operations,
                "expired_snapshot_ids": expired_snapshots,
            }
            if key is not None:
                self.root_idempotency.save(key, request, response)
            return JsonResponse.ok(response)

    def audit(self, plan_id: str | None) -> dict[str, Any]:
        with self.lock:
            if plan_id is not None:
                self._require_plan(plan_id)
            return {"events": list_events(self, plan_id)}


SERVICE = PlanService()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _send(self, response: JsonResponse) -> None:
        encoded = JsonWire.encode(response.body)
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_body(self, allow_empty: bool = False) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            if allow_empty:
                return {}
            raise ApiError("Content-Length is required")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ApiError("Content-Length is invalid") from exc
        if length < 0 or length > 1_000_000:
            raise ApiError("request body is too large")
        raw = self.rfile.read(length)
        if not raw and allow_empty:
            return {}
        return JsonWire.decode(raw)

    def _get(self, route: RoutePath) -> JsonResponse:
        if route.is_exact("GET") or route.is_exact("GET", "health"):
            route.require_no_query()
            return JsonResponse.ok(SERVICE.health())
        if route.is_exact("GET", "clock"):
            route.require_no_query()
            return JsonResponse.ok(SERVICE.clock_view())
        if route.is_exact("GET", "plans"):
            route.require_no_query()
            return JsonResponse.ok(SERVICE.list_plans())
        if route.is_exact("GET", "audit"):
            route.require_query_keys("plan_id")
            return JsonResponse.ok(SERVICE.audit(route.query_text("plan_id")))
        if len(route.segments) == 2 and route.segments[0] == "plans":
            route.require_no_query()
            return JsonResponse.ok(SERVICE.get_plan(route.segments[1]))
        if len(route.segments) == 3 and route.segments[0] == "plans":
            route.require_no_query()
            plan_id, leaf = route.segments[1], route.segments[2]
            if leaf == "operations":
                return JsonResponse.ok(SERVICE.list_operations(plan_id))
            if leaf == "snapshots":
                return JsonResponse.ok(SERVICE.list_snapshots(plan_id))
            if leaf == "releases":
                return JsonResponse.ok(SERVICE.list_releases(plan_id))
        if len(route.segments) == 2 and route.segments[0] == "operations":
            route.require_no_query()
            return JsonResponse.ok(SERVICE.get_operation(route.segments[1]))
        if len(route.segments) == 2 and route.segments[0] == "snapshots":
            route.require_no_query()
            return JsonResponse.ok(SERVICE.get_snapshot(route.segments[1]))
        if (
            len(route.segments) == 3
            and route.segments[0] == "snapshots"
            and route.segments[2] == "reviews"
        ):
            route.require_no_query()
            return JsonResponse.ok(SERVICE.list_reviews(route.segments[1]))
        raise ApiError("route not found", HTTPStatus.NOT_FOUND, "NOT_FOUND")

    def _post(self, route: RoutePath, body: dict[str, Any]) -> JsonResponse:
        route.require_no_query()
        if route.is_exact("POST", "admin", "reset"):
            JsonShape.exact_keys(body, set())
            return JsonResponse.ok(SERVICE.reset())
        if route.is_exact("POST", "clock", "advance"):
            return SERVICE.advance_clock(body)
        if route.is_exact("POST", "plans"):
            return SERVICE.create_plan(body)
        if (
            len(route.segments) == 4
            and route.segments[0] == "plans"
            and route.segments[2] == "operations"
            and route.segments[3] == "batch"
        ):
            return SERVICE.create_operation_batch(route.segments[1], body)
        if len(route.segments) == 3 and route.segments[0] == "plans":
            plan_id, leaf = route.segments[1], route.segments[2]
            if leaf in ("operation-batches", "operation_batches", "batches"):
                return SERVICE.create_operation_batch(plan_id, body)
            if leaf == "operations":
                # 单条路由收到 operations 数组时按批次处理，兼容两种提交形态。
                if isinstance(body, dict) and isinstance(body.get("operations"), list):
                    return SERVICE.create_operation_batch(plan_id, body)
                return SERVICE.create_operation(plan_id, body)
            if leaf == "snapshots":
                return SERVICE.create_snapshot(plan_id, body)
            if leaf == "publish":
                return SERVICE.publish(plan_id, body)
            if leaf == "rollback":
                return SERVICE.rollback(plan_id, body)
        if (
            len(route.segments) == 3
            and route.segments[0] == "snapshots"
            and route.segments[2] == "reviews"
        ):
            return SERVICE.create_review(route.segments[1], body)
        raise ApiError("route not found", HTTPStatus.NOT_FOUND, "NOT_FOUND")

    def _dispatch(self, method: str) -> None:
        try:
            route = RoutePath.parse(method, self.path)
            if method == "GET":
                self._send(self._get(route))
            else:
                self._send(self._post(route, self._read_body()))
        except ApiError as error:
            self._send(JsonResponse.error(error))
        except BrokenPipeError:
            return
        except Exception:
            self._send(
                JsonResponse(
                    int(HTTPStatus.INTERNAL_SERVER_ERROR),
                    {"error": {"code": "INTERNAL_ERROR", "message": "internal error"}},
                )
            )

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._send(
            JsonResponse(
                int(HTTPStatus.METHOD_NOT_ALLOWED),
                {
                    "error": {
                        "code": "METHOD_NOT_ALLOWED",
                        "message": "method not allowed",
                    }
                },
            )
        )

    def do_DELETE(self) -> None:  # noqa: N802
        self.do_PUT()

    def do_PATCH(self) -> None:  # noqa: N802
        self.do_PUT()


class Server(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    port = parse_port(os.environ.get("PORT", "8000"))
    server = Server(("0.0.0.0", port), Handler)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
