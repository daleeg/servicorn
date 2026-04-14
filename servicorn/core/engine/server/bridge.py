"""WSGI bridge implementation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from io import BytesIO
from typing import Any

from servicorn.core.engine.common.models import NormalizedRequest, NormalizedResponse
from servicorn.log import get_logger

LOG = get_logger(__name__)


class WSGIBridge:
    """Convert normalized RPC requests into WSGI calls."""

    def __init__(self, application: Callable):
        self.application = application

    def handle(self, request: NormalizedRequest) -> NormalizedResponse:
        """Invoke the wrapped WSGI application."""
        LOG.debug(
            "dispatching request to wsgi app request_id=%s method=%s path=%s",
            request.request_id,
            request.http_method,
            request.path,
        )
        captured: dict[str, Any] = {"status": None, "headers": ()}

        def start_response(
            status: str,
            headers: list[tuple[str, str]],
            exc_info: Any = None,
        ) -> None:
            captured["status"] = status
            captured["headers"] = tuple((str(name), str(value)) for name, value in headers)

        environ = self.build_environ(request)
        response_iterable = self.application(environ, start_response)
        try:
            body = self._consume_response(response_iterable)
        finally:
            close = getattr(response_iterable, "close", None)
            if callable(close):
                close()

        status_line = captured["status"] or "500 Internal Server Error"
        status_code = int(str(status_line).split(" ", 1)[0])
        LOG.debug(
            "wsgi response collected request_id=%s status_code=%s header_count=%s body_length=%s",
            request.request_id,
            status_code,
            len(captured["headers"]),
            len(body),
        )
        return NormalizedResponse(
            request_id=request.request_id,
            status_code=status_code,
            headers=captured["headers"],
            body=body,
        )

    def build_environ(self, request: NormalizedRequest) -> dict[str, Any]:
        """Build a WSGI ``environ`` mapping from a normalized request."""
        LOG.debug(
            "building wsgi environ request_id=%s method=%s path=%s query_string=%s header_count=%s body_length=%s",
            request.request_id,
            request.http_method,
            request.path,
            request.query_string,
            len(request.headers),
            len(request.body),
        )
        environ: dict[str, Any] = {
            "REQUEST_METHOD": request.http_method,
            "SCRIPT_NAME": "",
            "PATH_INFO": request.path,
            "QUERY_STRING": request.query_string,
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "8000",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": BytesIO(request.body),
            "wsgi.errors": BytesIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "CONTENT_LENGTH": str(len(request.body)),
            "servicorn.request_id": request.request_id,
            "servicorn.rpc_method": request.rpc_method,
            "servicorn.context.trace_id": request.context.trace_id,
            "servicorn.context.caller": request.context.caller,
        }

        if request.context.timeout_ms is not None:
            environ["servicorn.context.timeout_ms"] = str(request.context.timeout_ms)

        for key, value in request.context.extras.items():
            environ[f"servicorn.context.{key}"] = str(value)

        for name, value in request.headers:
            header_name = name.upper().replace("-", "_")
            if header_name == "CONTENT_TYPE":
                environ["CONTENT_TYPE"] = value
            elif header_name == "CONTENT_LENGTH":
                environ["CONTENT_LENGTH"] = value
            else:
                environ[f"HTTP_{header_name}"] = value
        return environ

    @staticmethod
    def _consume_response(response_iterable: Iterable[bytes | str]) -> bytes:
        chunks: list[bytes] = []
        for chunk in response_iterable:
            if isinstance(chunk, bytes):
                chunks.append(chunk)
            else:
                chunks.append(str(chunk).encode("utf-8"))
        return b"".join(chunks)
