"""Client-side JSON-RPC request and response models."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Literal
from typing import cast

from pydantic import AliasChoices, Field, PrivateAttr, field_serializer, field_validator, model_validator

from servicorn.core.engine.common.models import (
    ErrorInfo,
    FrozenModel,
    HttpHeader,
    HttpResponse,
    NormalizedRequest,
    NormalizedResponse,
    RequestContext,
)
from servicorn.utils.http import encode_body, normalize_path, normalize_query_string
from servicorn.utils.json import json_loads

ctx_type = SimpleNamespace


class RpcHttpRequest(FrozenModel):
    """Route-level RPC request passed into the client engine."""

    method: str = Field(alias="http_method")
    path: str
    query: dict[str, Any] = Field(default_factory=dict)
    headers: tuple[HttpHeader, ...] = Field(default_factory=tuple)
    body: Any = None
    context: dict[str, str] = Field(default_factory=dict)
    _ctx: ctx_type | None = PrivateAttr(default=None)

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, value: object) -> str:
        return str(value or "GET").upper()

    @field_validator("headers", mode="before")
    @classmethod
    def normalize_headers(cls, value: object) -> tuple[HttpHeader, ...]:
        if value is None:
            return ()
        if not isinstance(value, (list, tuple)):
            raise TypeError("headers must be a list of header pairs")
        return tuple(HttpHeader.from_value(item) for item in value)

    @field_serializer("headers")
    def serialize_headers(self, headers: tuple[HttpHeader, ...]) -> list[list[str]]:
        return [[header.name, header.value] for header in headers]

    @field_validator("context", mode="before")
    @classmethod
    def normalize_context(cls, value: object) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise TypeError("context must be an object")
        return {str(key): "" if item is None else str(item) for key, item in value.items()}

    @property
    def http_method(self) -> str:
        return self.method

    @property
    def header_items(self) -> tuple[tuple[str, str], ...]:
        return tuple(header.as_pair() for header in self.headers)

    @property
    def normalized_path(self) -> str:
        return normalize_path(self.path)

    @property
    def normalized_query_string(self) -> str:
        return normalize_query_string(None, self.query)

    @property
    def encoded_body(self) -> bytes:
        return encode_body(self.body)

    @staticmethod
    def make_context() -> ctx_type:
        return cast(
            ctx_type,
            SimpleNamespace(
                request_id="",
                trace_id="",
                caller="",
                timeout_ms=None,
                app={},
                extras={},
            ),
        )

    @property
    def ctx(self) -> ctx_type:
        """
        :return: The current request context
        """
        if not self._ctx:
            object.__setattr__(self, "_ctx", self.make_context())
        return cast(ctx_type, self._ctx)

    def build_context(self, **params: str | int) -> dict[str, str]:
        request_id = params.get("request_id", "")
        app_title = str(params.get("app_title", ""))
        app_version = str(params.get("app_version", ""))
        default_service_name = str(params.get("default_service_name", ""))
        values = {
            **self.coerce_string_dict(self.context),
            "request_id": str(request_id),
            "app.title": app_title,
            "app.version": app_version,
            "app.default_service_name": default_service_name,
        }
        self.update_context(
            request_id=values["request_id"],
            trace_id=values.get("trace_id", ""),
            caller=values.get("caller", ""),
            timeout_ms=values.get("timeout_ms"),
            app={
                "title": app_title,
                "version": app_version,
                "default_service_name": default_service_name,
            },
            extras={
                key: value
                for key, value in values.items()
                if key
                not in {
                    "request_id",
                    "trace_id",
                    "caller",
                    "timeout_ms",
                    "app.title",
                    "app.version",
                    "app.default_service_name",
                }
            },
        )
        return values

    def update_context(
        self,
        **params: object,
    ) -> None:
        ctx = self.ctx
        for key, value in params.items():
            if key in {"app", "extras"}:
                setattr(ctx, key, self.coerce_string_dict(value))
                continue
            if key == "timeout_ms":
                setattr(ctx, key, self.coerce_timeout(value))
                continue
            if value is None:
                setattr(ctx, key, "")
                continue
            setattr(ctx, key, str(value))

    @staticmethod
    def coerce_string_dict(value: object) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {str(key): "" if item is None else str(item) for key, item in value.items()}

    @staticmethod
    def coerce_timeout(value: object) -> int | None:
        if value in {None, ""}:
            return None
        try:
            timeout = int(value)
        except (TypeError, ValueError):
            return None
        return timeout if timeout >= 0 else None

class JsonRpcResult(FrozenModel):
    """JSON-RPC result payload carrying an HTTP-like response."""

    status_code: int
    headers: tuple[HttpHeader, ...] = Field(default_factory=tuple)
    body: Any = None

    @field_validator("headers", mode="before")
    @classmethod
    def normalize_headers(cls, value: object) -> tuple[HttpHeader, ...]:
        if value is None:
            return ()
        if not isinstance(value, (list, tuple)):
            raise TypeError("headers must be a list of header pairs")
        return tuple(HttpHeader.from_value(item) for item in value)

    @field_serializer("headers")
    def serialize_headers(self, headers: tuple[HttpHeader, ...]) -> list[list[str]]:
        return [[header.name, header.value] for header in headers]

    @classmethod
    def from_http_response(cls, response: HttpResponse) -> "JsonRpcResult":
        content_type = _find_header(response.header_items, "Content-Type")
        return cls(
            status_code=response.status_code,
            headers=response.headers,
            body=_decode_body(response.body, content_type),
        )


class JsonRpcRequest(FrozenModel):
    """JSON-RPC request envelope exposed by the FastAPI client gateway."""

    jsonrpc: Literal["2.0"]
    request_id: str | int = Field(
        validation_alias=AliasChoices("request_id", "id"),
        serialization_alias="request_id",
    )
    method: str
    params: RpcHttpRequest

    @model_validator(mode="before")
    @classmethod
    def normalize_params_shape(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        params = value.get("params")
        if not isinstance(params, dict) or "request" not in params:
            return value

        data = dict(value)
        params_data = dict(params)
        request_data = params_data.pop("request", {})
        if isinstance(request_data, dict):
            merged = dict(request_data)
            if "context" in params_data:
                merged["context"] = params_data["context"]
            data["params"] = merged
        return data

    def to_normalized_request(
        self,
        context: RequestContext | None = None,
    ) -> NormalizedRequest:
        if context is not None:
            self.params.update_context(
                request_id=context.request_id,
                trace_id=context.trace_id,
                caller=context.caller,
                timeout_ms=context.timeout_ms,
                app=context.app,
                extras=context.extras,
            )
        else:
            self.params.update_context(
                request_id=self.request_id,
                trace_id=self.params.context.get("trace_id", ""),
                caller=self.params.context.get("caller", ""),
                timeout_ms=self.params.context.get("timeout_ms"),
                extras=self.params.context,
            )
        return NormalizedRequest.from_rpc_http_request(
            self.params,
            rpc_method=self.method,
            request_id=self.request_id,
        )


class JsonRpcResponse(FrozenModel):
    """JSON-RPC response envelope returned by the FastAPI client gateway."""

    jsonrpc: Literal["2.0"] = "2.0"
    request_id: str | int | None = Field(
        default=None,
        validation_alias=AliasChoices("request_id", "id"),
        serialization_alias="request_id",
    )
    result: JsonRpcResult | None = None
    error: ErrorInfo | None = None

    @field_validator("error", mode="before")
    @classmethod
    def normalize_error(cls, value: object) -> ErrorInfo | None:
        return ErrorInfo.from_value(value)

    @classmethod
    def from_normalized_response(cls, response: NormalizedResponse) -> "JsonRpcResponse":
        payload = cls(
            request_id=response.request_id,
            result=JsonRpcResult.from_http_response(response.response),
        )
        if response.error is not None:
            return payload.model_copy(update={"error": response.error})
        return payload

    @classmethod
    def from_result(
        cls,
        *,
        request_id: str | int | None,
        result: JsonRpcResult,
    ) -> "JsonRpcResponse":
        return cls(request_id=request_id, result=result)

    @classmethod
    def from_error(
        cls,
        *,
        request_id: str | int | None,
        code: int,
        message: str,
    ) -> "JsonRpcResponse":
        return cls(request_id=request_id, error=ErrorInfo(code=code, message=message))


def _decode_body(body: bytes, content_type: str) -> Any:
    if not body:
        return ""
    if content_type.startswith("application/json"):
        return json_loads(body.decode("utf-8"))
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return {"encoding": "hex", "data": body.hex()}


def _find_header(headers: tuple[tuple[str, str], ...], name: str) -> str:
    header_name = name.lower()
    for current_name, value in headers:
        if current_name.lower() == header_name:
            return value
    return ""
