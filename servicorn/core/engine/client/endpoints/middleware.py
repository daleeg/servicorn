"""JSON-RPC middleware for the client gateway."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import iterate_in_threadpool

from servicorn.core.engine.client.endpoints.api import GATEWAY_RPC_PATH
from servicorn.core.engine.client.models import JsonRpcRequest, JsonRpcResponse, JsonRpcResult
from servicorn.utils.json import json_loads


class JsonRpcMiddleware(BaseHTTPMiddleware):
    """Parse JSON-RPC envelopes before the route layer runs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path != GATEWAY_RPC_PATH or request.method.upper() != "POST":
            return await call_next(request)
        if not _is_json_request(request):
            return await call_next(request)

        try:
            payload = await request.json()
        except Exception as exc:
            return _jsonrpc_response(
                JsonRpcResponse.from_error(request_id=None, code=-32700, message=str(exc))
            )

        try:
            rpc_request = JsonRpcRequest.model_validate(payload)
        except Exception as exc:
            return _jsonrpc_response(
                JsonRpcResponse.from_error(
                    request_id=payload.get("request_id", payload.get("id")),
                    code=-32600,
                    message=str(exc),
                )
            )

        request.state.jsonrpc_request = rpc_request
        request.state.rpc_method = rpc_request.method
        request.state.rpc_http_request = rpc_request.params
        request.state.rpc_http_request.build_context(
            request_id=rpc_request.request_id,
            app_title=str(getattr(request.app, "title", "")),
            app_version=str(getattr(request.app, "version", "")),
            default_service_name=str(getattr(request.app.state, "default_service_name", "")),
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            return _jsonrpc_response(
                JsonRpcResponse.from_error(
                    request_id=rpc_request.request_id,
                    code=-32000,
                    message=str(exc),
                )
            )

        body = await _read_response_body(response)
        result = JsonRpcResult.model_validate(json_loads(body.decode("utf-8")))
        return _jsonrpc_response(
            JsonRpcResponse.from_result(request_id=rpc_request.request_id, result=result)
        )


def register_jsonrpc_middleware(app: FastAPI) -> None:
    """Attach JSON-RPC envelope parsing middleware to the FastAPI app."""

    app.add_middleware(JsonRpcMiddleware)

def _jsonrpc_response(payload: JsonRpcResponse) -> JSONResponse:
    return JSONResponse(payload.model_dump(by_alias=True, exclude_none=True))


def _is_json_request(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type in {"application/json", "application/json-rpc"}


async def _read_response_body(response: Response) -> bytes:
    body = getattr(response, "body", None)
    if body is not None:
        return body

    chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8"))
    response.body_iterator = iterate_in_threadpool(iter(chunks))
    return b"".join(chunks)
