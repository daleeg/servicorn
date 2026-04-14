"""Server-side engine orchestration."""

from __future__ import annotations

from servicorn.core.engine.common.exceptions import ServicornError
from servicorn.core.engine.common.models import NormalizedRequest, NormalizedResponse
from servicorn.core.engine.server.application import load_wsgi_application
from servicorn.core.engine.server.bridge import WSGIBridge
from servicorn.core.grpc.v1 import gateway_pb2
from servicorn.log import get_logger

LOG = get_logger(__name__)


class ServicornEngine:
    """Coordinate normalization, WSGI dispatch, and response encoding."""

    def __init__(self, wsgi_app: str):
        self.wsgi_app = wsgi_app

    def handle_proto_request(self, message: gateway_pb2.GrpcCallRequest, context=None) -> gateway_pb2.GrpcCallResponse:
        """Handle a protobuf gRPC request inside the server runtime."""
        del context
        LOG.debug("handling protobuf gateway request wsgi_app=%s", self.wsgi_app)
        try:
            request = NormalizedRequest.from_grpc_call_request(message)
            response = self._dispatch_request(request)
        except ServicornError as exc:
            LOG.debug("protobuf gateway request failed wsgi_app=%s error=%s", self.wsgi_app, exc)
            response = NormalizedResponse(
                request_id="",
                status_code=500,
                headers=(),
                body=b"",
                error={"code": -32000, "message": str(exc)},
            )
        return response.to_grpc_call_response()

    def _dispatch_request(self, request) -> NormalizedResponse:
        LOG.debug(
            "dispatching normalized request request_id=%s method=%s path=%s",
            request.request_id,
            request.http_method,
            request.path,
        )
        application = load_wsgi_application(self.wsgi_app)
        bridge = WSGIBridge(application)
        return bridge.handle(request)
