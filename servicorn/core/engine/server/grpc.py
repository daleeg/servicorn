"""gRPC server bindings for the servicorn Gateway service."""

from __future__ import annotations

import grpc

from servicorn.core.engine.server.engine import ServicornEngine
from servicorn.core.grpc.v1 import GRPC_METHOD_NAME, GRPC_SERVICE, gateway_pb2


def add_gateway_handler(server: grpc.Server, engine: ServicornEngine) -> None:
    """Attach the Gateway/GrpcCall method handler to a gRPC server."""
    rpc_method_handlers = {
        GRPC_METHOD_NAME: grpc.unary_unary_rpc_method_handler(
            engine.handle_proto_request,
            request_deserializer=gateway_pb2.GrpcCallRequest.FromString,
            response_serializer=gateway_pb2.GrpcCallResponse.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(GRPC_SERVICE, rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
