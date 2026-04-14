"""JSON-RPC route definitions for the client gateway."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from servicorn.core.engine.client.models import JsonRpcResult, RpcHttpRequest

GATEWAY_RPC_PATH = "/api/v1/gateway_rpc"

router = APIRouter()


def get_rpc_method(request: Request) -> str:
    """Read the RPC method extracted by middleware."""
    return request.state.rpc_method


def get_rpc_http_request(request: Request) -> RpcHttpRequest:
    """Read the structured RPC request extracted by middleware."""
    return request.state.rpc_http_request


@router.post(GATEWAY_RPC_PATH)
def jsonrpc_gateway(
    request: Request,
    method: str = Depends(get_rpc_method),
    rpc_request: RpcHttpRequest = Depends(get_rpc_http_request),
) -> JsonRpcResult:
    """Forward the normalized RPC call to the gRPC backend."""
    return request.app.state.client_engine.forward_rpc(method, rpc_request)
