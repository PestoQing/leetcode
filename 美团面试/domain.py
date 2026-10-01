from __future__ import annotations

import copy
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, TypeAlias
from urllib.parse import parse_qs, unquote, urlparse


JsonObject: TypeAlias = dict[str, Any]
JsonArray: TypeAlias = list[Any]
JsonValue: TypeAlias = None | bool | int | float | str | JsonArray | JsonObject
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


class ApiError(Exception):
    def __init__(
        self,
        message: str,
        status: HTTPStatus = HTTPStatus.BAD_REQUEST,
        code: str = "VALIDATION_ERROR",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code

    def payload(self) -> JsonObject:
        return {"error": {"code": self.code, "message": self.message}}


class JsonShape:
    @staticmethod
    def object(value: Any, field: str = "request body") -> JsonObject:
        if not isinstance(value, dict):
            raise ApiError(f"{field} must be a JSON object")
        return value

    @staticmethod
    def array(value: Any, field: str) -> JsonArray:
        if not isinstance(value, list):
            raise ApiError(f"{field} must be a JSON array")
        return value

    @staticmethod
    def text(
        value: Any,
        field: str,
        minimum: int = 1,
        maximum: int = 4096,
    ) -> str:
        if not isinstance(value, str):
            raise ApiError(f"{field} must be a string")
        if value != value.strip() or not minimum <= len(value) <= maximum:
            raise ApiError(f"{field} has invalid length or whitespace")
        return value

    @staticmethod
    def optional_text(
        value: Any,
        field: str,
        minimum: int = 1,
        maximum: int = 4096,
    ) -> str | None:
        if value is None:
            return None
        return JsonShape.text(value, field, minimum, maximum)

    @staticmethod
    def identifier(value: Any, field: str) -> str:
        text = JsonShape.text(value, field, 1, 64)
        if not IDENTIFIER.fullmatch(text):
            raise ApiError(f"{field} has invalid format")
        return text

    @staticmethod
    def integer(
        value: Any,
        field: str,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ApiError(f"{field} must be an integer")
        if minimum is not None and value < minimum:
            raise ApiError(f"{field} is too small")
        if maximum is not None and value > maximum:
            raise ApiError(f"{field} is too large")
        return value

    @staticmethod
    def optional_integer(
        value: Any,
        field: str,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int | None:
        if value is None:
            return None
        return JsonShape.integer(value, field, minimum, maximum)

    @staticmethod
    def boolean(value: Any, field: str) -> bool:
        if not isinstance(value, bool):
            raise ApiError(f"{field} must be a boolean")
        return value

    @staticmethod
    def one_of(value: Any, field: str, options: Iterable[str]) -> str:
        text = JsonShape.text(value, field)
        if text not in set(options):
            raise ApiError(f"{field} is invalid")
        return text

    @staticmethod
    def text_list(
        value: Any,
        field: str,
        *,
        minimum: int = 0,
        maximum: int = 4096,
        unique: bool = False,
        sorted_output: bool = False,
        identifiers: bool = False,
        allowed: Iterable[str] | None = None,
    ) -> list[str]:
        values = JsonShape.array(value, field)
        if len(values) < minimum or len(values) > maximum:
            raise ApiError(f"{field} has invalid item count")
        validator = JsonShape.identifier if identifiers else JsonShape.text
        result = [validator(item, field) for item in values]
        if unique and len(result) != len(set(result)):
            raise ApiError(f"{field} contains duplicates")
        if allowed is not None and any(item not in set(allowed) for item in result):
            raise ApiError(f"{field} contains an invalid value")
        return sorted(result) if sorted_output else result

    @staticmethod
    def object_list(
        value: Any,
        field: str,
        *,
        minimum: int = 0,
        maximum: int = 4096,
    ) -> list[JsonObject]:
        values = JsonShape.array(value, field)
        if len(values) < minimum or len(values) > maximum:
            raise ApiError(f"{field} has invalid item count")
        return [
            JsonShape.object(item, f"{field}[{index}]")
            for index, item in enumerate(values)
        ]

    @staticmethod
    def exact_keys(
        value: Mapping[str, Any],
        required: Iterable[str],
        optional: Iterable[str] = (),
    ) -> None:
        required_set = set(required)
        allowed = required_set | set(optional)
        missing = sorted(required_set - set(value))
        extra = sorted(set(value) - allowed)
        if missing:
            raise ApiError(f"missing fields: {', '.join(missing)}")
        if extra:
            raise ApiError(f"unknown fields: {', '.join(extra)}")

    @staticmethod
    def clone(value: JsonValue) -> JsonValue:
        JsonShape.json_value(value)
        return copy.deepcopy(value)

    @staticmethod
    def public_object(value: Mapping[str, Any]) -> JsonObject:
        cloned = JsonShape.clone(dict(value))
        if not isinstance(cloned, dict):
            raise ApiError("response must be an object")
        return cloned

    @staticmethod
    def canonical(value: JsonValue) -> str:
        JsonShape.json_value(value)
        return json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )

    @staticmethod
    def json_value(value: Any, field: str = "value") -> None:
        if value is None or isinstance(value, (bool, int, float, str)):
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                JsonShape.json_value(item, f"{field}[{index}]")
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ApiError(f"{field} has a non-string key")
                JsonShape.json_value(item, f"{field}.{key}")
            return
        raise ApiError(f"{field} is not JSON compatible")


class FieldReader:
    def __init__(self, value: Any, field: str = "request body") -> None:
        self.values = JsonShape.object(value, field)
        self.field = field
        self.used: set[str] = set()

    def has(self, name: str) -> bool:
        return name in self.values

    def raw(self, name: str, default: Any = None) -> Any:
        self.used.add(name)
        return self.values.get(name, default)

    def required_raw(self, name: str) -> Any:
        if name not in self.values:
            raise ApiError(f"{name} is required")
        self.used.add(name)
        return self.values[name]

    def text(
        self,
        name: str,
        minimum: int = 1,
        maximum: int = 4096,
    ) -> str:
        return JsonShape.text(self.required_raw(name), name, minimum, maximum)

    def optional_text(
        self,
        name: str,
        minimum: int = 1,
        maximum: int = 4096,
    ) -> str | None:
        return JsonShape.optional_text(self.raw(name), name, minimum, maximum)

    def identifier(self, name: str) -> str:
        return JsonShape.identifier(self.required_raw(name), name)

    def integer(
        self,
        name: str,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        return JsonShape.integer(self.required_raw(name), name, minimum, maximum)

    def optional_integer(
        self,
        name: str,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int | None:
        return JsonShape.optional_integer(self.raw(name), name, minimum, maximum)

    def boolean(self, name: str) -> bool:
        return JsonShape.boolean(self.required_raw(name), name)

    def one_of(self, name: str, options: Iterable[str]) -> str:
        return JsonShape.one_of(self.required_raw(name), name, options)

    def text_list(
        self,
        name: str,
        *,
        minimum: int = 0,
        maximum: int = 4096,
        unique: bool = False,
        sorted_output: bool = False,
        identifiers: bool = False,
        allowed: Iterable[str] | None = None,
    ) -> list[str]:
        return JsonShape.text_list(
            self.required_raw(name),
            name,
            minimum=minimum,
            maximum=maximum,
            unique=unique,
            sorted_output=sorted_output,
            identifiers=identifiers,
            allowed=allowed,
        )

    def optional_text_list(
        self,
        name: str,
        *,
        minimum: int = 0,
        maximum: int = 4096,
        unique: bool = False,
        sorted_output: bool = False,
        identifiers: bool = False,
        allowed: Iterable[str] | None = None,
    ) -> list[str] | None:
        if name not in self.values:
            return None
        self.used.add(name)
        return JsonShape.text_list(
            self.values[name],
            name,
            minimum=minimum,
            maximum=maximum,
            unique=unique,
            sorted_output=sorted_output,
            identifiers=identifiers,
            allowed=allowed,
        )

    def object(self, name: str) -> JsonObject:
        return JsonShape.object(self.required_raw(name), name)

    def optional_object(self, name: str) -> JsonObject | None:
        value = self.raw(name)
        return None if value is None else JsonShape.object(value, name)

    def finish(self) -> None:
        unused = sorted(set(self.values) - self.used)
        if unused:
            raise ApiError(f"unknown fields: {', '.join(unused)}")


class IdSequence:
    def __init__(self, prefix: str) -> None:
        self.prefix = JsonShape.text(prefix, "prefix", 1, 32)
        self.value = 0

    def next(self) -> str:
        self.value += 1
        return f"{self.prefix}_{self.value}"

    def current(self) -> int:
        return self.value

    def reset(self) -> None:
        self.value = 0

    def restore(self, value: Any) -> None:
        self.value = JsonShape.integer(value, "sequence", 0)


class LogicalClock:
    def __init__(self) -> None:
        self.value = 0

    @property
    def now(self) -> int:
        return self.value

    def reset(self) -> None:
        self.value = 0

    def advance(self, minutes: Any, maximum: int = 10_000) -> int:
        self.value += JsonShape.integer(minutes, "minutes", 1, maximum)
        return self.value

    def snapshot(self) -> int:
        return self.value

    def restore(self, value: Any) -> None:
        self.value = JsonShape.integer(value, "clock", 0)

    def reached(self, target: Any) -> bool:
        return self.value >= JsonShape.integer(target, "target", 0)

    def remaining(self, target: Any) -> int:
        return max(0, JsonShape.integer(target, "target", 0) - self.value)


class OrderedTable:
    def __init__(self, label: str) -> None:
        self.label = JsonShape.text(label, "table label", 1, 64)
        self.items: dict[str, JsonObject] = {}

    def clear(self) -> None:
        self.items.clear()

    def count(self) -> int:
        return len(self.items)

    def insert(self, identifier: str, value: Mapping[str, Any]) -> JsonObject:
        key = JsonShape.text(identifier, f"{self.label} id", 1, 256)
        if key in self.items:
            raise ApiError(
                f"{self.label} already exists",
                HTTPStatus.CONFLICT,
                "ALREADY_EXISTS",
            )
        copied = JsonShape.public_object(value)
        self.items[key] = copied
        return JsonShape.public_object(copied)

    def require(self, identifier: str) -> JsonObject:
        key = JsonShape.text(identifier, f"{self.label} id", 1, 256)
        value = self.items.get(key)
        if value is None:
            raise ApiError(
                f"{self.label} not found",
                HTTPStatus.NOT_FOUND,
                "NOT_FOUND",
            )
        return JsonShape.public_object(value)

    def get(self, identifier: str) -> JsonObject | None:
        key = JsonShape.text(identifier, f"{self.label} id", 1, 256)
        value = self.items.get(key)
        return None if value is None else JsonShape.public_object(value)

    def replace(self, identifier: str, value: Mapping[str, Any]) -> JsonObject:
        key = JsonShape.text(identifier, f"{self.label} id", 1, 256)
        if key not in self.items:
            raise ApiError(
                f"{self.label} not found",
                HTTPStatus.NOT_FOUND,
                "NOT_FOUND",
            )
        copied = JsonShape.public_object(value)
        self.items[key] = copied
        return JsonShape.public_object(copied)

    def remove(self, identifier: str) -> JsonObject:
        key = JsonShape.text(identifier, f"{self.label} id", 1, 256)
        value = self.items.pop(key, None)
        if value is None:
            raise ApiError(
                f"{self.label} not found",
                HTTPStatus.NOT_FOUND,
                "NOT_FOUND",
            )
        return JsonShape.public_object(value)

    def values(self) -> list[JsonObject]:
        return [JsonShape.public_object(value) for value in self.items.values()]

    def identifiers(self) -> list[str]:
        return list(self.items)


class IdempotencyTable:
    def __init__(self) -> None:
        self.items: dict[str, JsonObject] = {}

    def clear(self) -> None:
        self.items.clear()

    def lookup(self, key: str, request: JsonObject) -> JsonObject | None:
        record = self.items.get(JsonShape.text(key, "idempotency_key", 1, 128))
        if record is None:
            return None
        if record["request"] != JsonShape.canonical(request):
            raise ApiError(
                "idempotency_key was used for a different request",
                HTTPStatus.CONFLICT,
                "IDEMPOTENCY_KEY_REUSED",
            )
        return JsonShape.public_object(record["response"])

    def save(self, key: str, request: JsonObject, response: JsonObject) -> None:
        normalized_key = JsonShape.text(key, "idempotency_key", 1, 128)
        self.items[normalized_key] = {
            "request": JsonShape.canonical(request),
            "response": JsonShape.public_object(response),
        }


@dataclass(frozen=True)
class RoutePath:
    method: str
    segments: tuple[str, ...]
    query: dict[str, list[str]]

    @classmethod
    def parse(cls, method: str, raw_path: str) -> RoutePath:
        parsed = urlparse(raw_path)
        segments = tuple(
            unquote(segment) for segment in parsed.path.split("/") if segment
        )
        return cls(
            method.upper(), segments, parse_qs(parsed.query, keep_blank_values=True)
        )

    def is_exact(self, method: str, *segments: str) -> bool:
        return self.method == method.upper() and self.segments == tuple(segments)

    def has_prefix(self, method: str, *segments: str) -> bool:
        prefix = tuple(segments)
        return self.method == method.upper() and self.segments[: len(prefix)] == prefix

    def require_no_query(self) -> None:
        if self.query:
            raise ApiError("query parameters are not allowed")

    def query_text(self, name: str, required: bool = False) -> str | None:
        values = self.query.get(name)
        if values is None:
            if required:
                raise ApiError(f"missing query parameter: {name}")
            return None
        if len(values) != 1:
            raise ApiError(f"query parameter {name} must appear once")
        return JsonShape.text(values[0], name)

    def require_query_keys(self, *names: str) -> None:
        extra = sorted(set(self.query) - set(names))
        if extra:
            raise ApiError(f"unknown query parameters: {', '.join(extra)}")


@dataclass(frozen=True)
class JsonResponse:
    status: int
    body: JsonObject

    @classmethod
    def ok(cls, body: Mapping[str, Any]) -> JsonResponse:
        return cls(int(HTTPStatus.OK), JsonShape.public_object(body))

    @classmethod
    def created(cls, body: Mapping[str, Any]) -> JsonResponse:
        return cls(int(HTTPStatus.CREATED), JsonShape.public_object(body))

    @classmethod
    def accepted(cls, body: Mapping[str, Any]) -> JsonResponse:
        return cls(int(HTTPStatus.ACCEPTED), JsonShape.public_object(body))

    @classmethod
    def error(cls, error: ApiError) -> JsonResponse:
        return cls(int(error.status), error.payload())


class JsonWire:
    @staticmethod
    def decode(raw: bytes) -> JsonObject:
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError("request body must be UTF-8 JSON") from exc
        return JsonShape.object(value)

    @staticmethod
    def encode(value: Mapping[str, Any]) -> bytes:
        body = JsonShape.public_object(value)
        return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )


class StateSnapshot:
    def __init__(self, value: Mapping[str, Any]) -> None:
        self.value = JsonShape.public_object(value)

    def restore(self) -> JsonObject:
        return JsonShape.public_object(self.value)


class OperationDraft:
    def __init__(self, value: Mapping[str, Any]) -> None:
        self.value = JsonShape.public_object(value)

    def with_value(self, name: str, value: JsonValue) -> OperationDraft:
        next_value = JsonShape.public_object(self.value)
        next_value[name] = JsonShape.clone(value)
        return OperationDraft(next_value)

    def object(self) -> JsonObject:
        return JsonShape.public_object(self.value)


class StableOrder:
    @staticmethod
    def text(values: Iterable[str]) -> list[str]:
        return sorted(JsonShape.text(value, "item") for value in values)

    @staticmethod
    def objects(values: Iterable[Mapping[str, Any]], key: str) -> list[JsonObject]:
        copied = [JsonShape.public_object(value) for value in values]
        return sorted(copied, key=lambda value: str(value[key]))


class PublicProjection:
    @staticmethod
    def plan(record: Mapping[str, Any]) -> JsonObject:
        return JsonShape.public_object(record)

    @staticmethod
    def operation(record: Mapping[str, Any]) -> JsonObject:
        return JsonShape.public_object(record)

    @staticmethod
    def snapshot(record: Mapping[str, Any]) -> JsonObject:
        return JsonShape.public_object(record)

    @staticmethod
    def review(record: Mapping[str, Any]) -> JsonObject:
        return JsonShape.public_object(record)

    @staticmethod
    def release(record: Mapping[str, Any]) -> JsonObject:
        return JsonShape.public_object(record)
