"""Typed request and response models used by the core engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from servicorn.core.engine.client.models import RpcHttpRequest


class FrozenModel(BaseModel):
    """Shared base model with immutable instances."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)


class HttpHeader(FrozenModel):
    """One HTTP header entry."""

    name: str
    value: str

    @classmethod
    def from_value(cls, value: object) -> "HttpHeader":
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls.model_validate(value)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return cls(name=str(value[0]), value=str(value[1]))
        raise TypeError("header items must be Header objects or [name, value] pairs")

    def as_pair(self) -> tuple[str, str]:
        return (self.name, self.value)


class RequestContext(FrozenModel):
    """Metadata that should not be mixed into the HTTP request body."""

    request_id: str = ""
    trace_id: str = ""
    caller: str = ""
    timeout_ms: int | None = None
    app: dict[str, str] = Field(default_factory=dict)
    extras: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def absorb_extra_fields(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        data = dict(value)
        extras_value = data.pop("extras", {})
        extras = cls._string_dict(extras_value)
        for key in list(data):
            if key not in {"request_id", "trace_id", "caller", "timeout_ms", "app"}:
                extras[key] = "" if data[key] is None else str(data[key])
                data.pop(key)
        data["extras"] = extras
        return data

    @field_validator("timeout_ms")
    @classmethod
    def validate_timeout(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("timeout_ms must be non-negative")
        return value

    @field_validator("extras", mode="before")
    @classmethod
    def normalize_extras(cls, value: object) -> dict[str, str]:
        return cls._string_dict(value)

    @field_validator("app", mode="before")
    @classmethod
    def normalize_app(cls, value: object) -> dict[str, str]:
        return cls._string_dict(value)

    @staticmethod
    def _string_dict(value: object) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise TypeError("extras must be an object")
        return {str(key): "" if item is None else str(item) for key, item in value.items()}


class HttpRequest(FrozenModel):
    """Transport-neutral HTTP-like request payload."""

    method: str = Field(alias="http_method")
    path: str
    query_string: str = ""
    headers: tuple[HttpHeader, ...] = Field(default_factory=tuple)
    body: bytes = b""
    scheme: str = "http"

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, value: object) -> str:
        return str(value or "GET").upper()

    @field_validator("path", mode="before")
    @classmethod
    def normalize_path(cls, value: object) -> str:
        text = str(value or "/")
        return text if text.startswith("/") else f"/{text}"

    @field_validator("headers", mode="before")
    @classmethod
    def normalize_headers(cls, value: object) -> tuple[HttpHeader, ...]:
        if value is None:
            return ()
        if not isinstance(value, (list, tuple)):
            raise TypeError("headers must be a list of header pairs")
        return tuple(HttpHeader.from_value(item) for item in value)

    @field_validator("body", mode="before")
    @classmethod
    def normalize_body(cls, value: object) -> bytes:
        if value is None:
            return b""
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray):
            return bytes(value)
        if isinstance(value, memoryview):
            return value.tobytes()
        raise TypeError("body must be bytes")

    @property
    def http_method(self) -> str:
        return self.method

    @property
    def header_items(self) -> tuple[tuple[str, str], ...]:
        return tuple(header.as_pair() for header in self.headers)


class HttpResponse(FrozenModel):
    """Transport-neutral HTTP-like response payload."""

    status_code: int
    headers: tuple[HttpHeader, ...] = Field(default_factory=tuple)
    body: bytes = b""

    @field_validator("headers", mode="before")
    @classmethod
    def normalize_headers(cls, value: object) -> tuple[HttpHeader, ...]:
        if value is None:
            return ()
        if not isinstance(value, (list, tuple)):
            raise TypeError("headers must be a list of header pairs")
        return tuple(HttpHeader.from_value(item) for item in value)

    @field_validator("body", mode="before")
    @classmethod
    def normalize_body(cls, value: object) -> bytes:
        if value is None:
            return b""
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray):
            return bytes(value)
        if isinstance(value, memoryview):
            return value.tobytes()
        raise TypeError("body must be bytes")

    @property
    def header_items(self) -> tuple[tuple[str, str], ...]:
        return tuple(header.as_pair() for header in self.headers)


class ErrorInfo(FrozenModel):
    """Typed error payload for protocol-level failures."""

    code: int
    message: str

    @classmethod
    def from_value(cls, value: object) -> "ErrorInfo" | None:
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls.model_validate(value)
        raise TypeError("error must be an object")


class NormalizedRequest(FrozenModel):
    """A transport-neutral, normalized request ready for WSGI mapping."""

    request_id: str
    rpc_method: str
    request: HttpRequest
    context: RequestContext = Field(default_factory=RequestContext)

    @model_validator(mode="before")
    @classmethod
    def accept_flat_shape(cls, value: object) -> object:
        if not isinstance(value, dict) or "request" in value:
            return value

        request_keys = {"http_method", "method", "path", "query_string", "headers", "body", "scheme"}
        if not any(key in value for key in request_keys):
            return value

        data = dict(value)
        request = {
            "http_method": data.pop("http_method", data.pop("method", "GET")),
            "path": data.pop("path", "/"),
            "query_string": data.pop("query_string", ""),
            "headers": data.pop("headers", ()),
            "body": data.pop("body", b""),
            "scheme": data.pop("scheme", "http"),
        }
        data["request"] = request
        return data

    @property
    def http_method(self) -> str:
        return self.request.http_method

    @property
    def path(self) -> str:
        return self.request.path

    @property
    def query_string(self) -> str:
        return self.request.query_string

    @property
    def headers(self) -> tuple[tuple[str, str], ...]:
        return self.request.header_items

    @property
    def body(self) -> bytes:
        return self.request.body

    @property
    def service_name(self) -> str:
        return self.context.extras.get(
            "service_name",
            self.context.app.get("default_service_name", "gateway"),
        )

    @staticmethod
    def to_request_context(
            rpc_request: "RpcHttpRequest",
            *,
            request_id: str | int | None = None,
    ) -> RequestContext:
        ctx = rpc_request.ctx
        return RequestContext(
            request_id=ctx.request_id,
            trace_id=ctx.trace_id,
            caller=ctx.caller,
            timeout_ms=ctx.timeout_ms,
            app=ctx.app,
            extras=ctx.extras,
        )

    @classmethod
    def from_rpc_http_request(
            cls,
            rpc_request: "RpcHttpRequest",
            *,
            rpc_method: str,
            request_id: str | int | None = None,
    ) -> "NormalizedRequest":
        context = cls.to_request_context(rpc_request, request_id=request_id)
        headers = rpc_request.headers
        return cls(
            request_id=context.request_id,
            rpc_method=rpc_method,
            request={
                "http_method": rpc_request.method,
                "path": rpc_request.normalized_path,
                "query_string": rpc_request.normalized_query_string,
                "headers": headers,
                "body": rpc_request.encoded_body,
            },
            context=context,
        )

    def to_grpc_call_request(self):
        """Convert this normalized request into the protobuf gRPC request."""
        from servicorn.core.grpc.v1 import gateway_pb2

        context = gateway_pb2.RequestContext(
            trace_id=self.context.trace_id,
            caller=self.context.caller,
            timeout_ms=self.context.timeout_ms or 0,
            extras=self.context.extras,
        )
        request = gateway_pb2.HttpRequest(
            http_method=self.request.method,
            path=self.request.path,
            query_string=self.request.query_string,
            headers=[
                gateway_pb2.Header(name=header.name, value=header.value)
                for header in self.request.headers
            ],
            body=self.request.body,
        )
        return gateway_pb2.GrpcCallRequest(request=request, context=context)

    @classmethod
    def from_grpc_call_request(
            cls,
            message,
            *,
            request_id: str = "",
            rpc_method: str = "GrpcCall",
    ) -> "NormalizedRequest":
        request = HttpRequest(
            http_method=message.request.http_method,
            path=message.request.path,
            query_string=message.request.query_string,
            headers=[(header.name, header.value) for header in message.request.headers],
            body=message.request.body,
        )
        context = RequestContext(
            request_id=request_id,
            trace_id=message.context.trace_id,
            caller=message.context.caller,
            timeout_ms=message.context.timeout_ms or None,
            extras=dict(message.context.extras),
        )
        return cls(
            request_id=request_id,
            rpc_method=rpc_method,
            request=request,
            context=context,
        )


class NormalizedResponse(FrozenModel):
    """A normalized response produced by the WSGI bridge."""

    request_id: str
    response: HttpResponse
    error: ErrorInfo | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_flat_shape(cls, value: object) -> object:
        if not isinstance(value, dict) or "response" in value:
            return value

        response_keys = {"status_code", "headers", "body"}
        if not any(key in value for key in response_keys):
            return value

        data = dict(value)
        response = {
            "status_code": data.pop("status_code", 200),
            "headers": data.pop("headers", ()),
            "body": data.pop("body", b""),
        }
        if "error" in data:
            data["error"] = ErrorInfo.from_value(data["error"])
        data["response"] = response
        return data

    @field_validator("error", mode="before")
    @classmethod
    def normalize_error(cls, value: object) -> ErrorInfo | None:
        return ErrorInfo.from_value(value)

    @property
    def status_code(self) -> int:
        return self.response.status_code

    @property
    def headers(self) -> tuple[tuple[str, str], ...]:
        return self.response.header_items

    @property
    def body(self) -> bytes:
        return self.response.body

    def to_grpc_call_response(self):
        """Convert this normalized response into the protobuf gRPC response."""
        from servicorn.core.grpc.v1 import gateway_pb2

        result = gateway_pb2.ResponseResult(
            status_code=self.response.status_code,
            headers=[
                gateway_pb2.Header(name=header.name, value=header.value)
                for header in self.response.headers
            ],
            body=self.response.body,
        )
        proto = gateway_pb2.GrpcCallResponse(result=result)
        if self.error is not None:
            proto.error.code = self.error.code
            proto.error.message = self.error.message
        return proto

    @classmethod
    def from_grpc_call_response(
            cls,
            message: "gateway_pb2.GrpcCallResponse",
            *,
            request_id: str,
    ) -> "NormalizedResponse":
        response = HttpResponse(
            status_code=message.result.status_code,
            headers=[(header.name, header.value) for header in message.result.headers],
            body=message.result.body,
        )
        error = None
        if message.HasField("error"):
            error = ErrorInfo(code=message.error.code, message=message.error.message)
        return cls(request_id=request_id, response=response, error=error)
