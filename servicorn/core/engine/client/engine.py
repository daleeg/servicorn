"""Client-side engine helpers."""

from __future__ import annotations

from typing import Any

import grpc

from servicorn.core.engine.client.models import JsonRpcResult, RpcHttpRequest
from servicorn.core.engine.discovery import EtcdServiceDiscovery, ServiceEndpoint
from servicorn.core.engine.common.exceptions import ConfigurationError
from servicorn.core.engine.common.models import NormalizedRequest, NormalizedResponse
from servicorn.core.grpc.v1 import GRPC_METHOD_PATH, gateway_pb2

GRPC_CHANNEL_OPTIONS = (("grpc.enable_http_proxy", 0),)


class GrpcClientEngine:
    """Resolve service targets for outbound gRPC-style calls."""

    def __init__(
        self,
        discovery: EtcdServiceDiscovery | None = None,
        grpc_caller=None,
    ):
        self.discovery = discovery or EtcdServiceDiscovery()
        self.grpc_caller = grpc_caller or self._default_grpc_caller

    def resolve(self, service_name: str) -> ServiceEndpoint:
        """Resolve a service endpoint or raise a configuration error."""
        endpoint = self.discovery.resolve(service_name)
        if endpoint is None:
            raise ConfigurationError(f"service '{service_name}' is not registered")
        return endpoint

    def build_target(self, service_name: str) -> str:
        """Return the host:port target for the given service."""
        return self.resolve(service_name).address

    def build_metadata(self, service_name: str) -> dict[str, Any]:
        """Expose discovery metadata for an outbound client."""
        endpoint = self.resolve(service_name)
        return {
            "service_name": endpoint.service_name,
            "host": endpoint.host,
            "port": endpoint.port,
            "metadata": endpoint.metadata,
        }

    def forward_rpc(
        self,
        method: str,
        rpc_request: RpcHttpRequest,
    ) -> JsonRpcResult:
        """Forward one structured RPC request to the gRPC backend."""
        normalized_request = NormalizedRequest.from_rpc_http_request(
            rpc_request,
            rpc_method=method,
        )
        target = self.build_target(normalized_request.service_name)
        normalized_response = self.grpc_json_call(target, normalized_request)
        return self._build_result(normalized_response)

    def grpc_json_call(
        self,
        target: str,
        normalized_request: NormalizedRequest,
    ) -> NormalizedResponse:
        proto_request = normalized_request.to_grpc_call_request()
        proto_response = self.grpc_caller(target, proto_request)
        return NormalizedResponse.from_grpc_call_response(
            proto_response,
            request_id=normalized_request.request_id,
        )

    @staticmethod
    def _build_result(response: NormalizedResponse) -> JsonRpcResult:
        return JsonRpcResult.from_http_response(response.response)

    @staticmethod
    def _default_grpc_caller(target: str, proto_request: gateway_pb2.GrpcCallRequest):
        with grpc.insecure_channel(target, options=GRPC_CHANNEL_OPTIONS) as channel:
            method = channel.unary_unary(
                GRPC_METHOD_PATH,
                request_serializer=gateway_pb2.GrpcCallRequest.SerializeToString,
                response_deserializer=gateway_pb2.GrpcCallResponse.FromString,
            )
            return method(proto_request)
