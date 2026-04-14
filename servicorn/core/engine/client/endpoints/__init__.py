"""FastAPI endpoint assembly for the client gateway."""

from servicorn.core.engine.client.endpoints.app import create_client_app
from servicorn.core.engine.client.endpoints.api import GATEWAY_RPC_PATH, router
from servicorn.core.engine.client.endpoints.middleware import register_jsonrpc_middleware

__all__ = [
    "create_client_app",
    "GATEWAY_RPC_PATH",
    "register_jsonrpc_middleware",
    "router",
]
