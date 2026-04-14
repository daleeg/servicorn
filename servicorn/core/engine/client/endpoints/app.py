"""FastAPI application assembly for the client gateway."""

from __future__ import annotations

from fastapi import FastAPI

from servicorn.core.engine.client.engine import GrpcClientEngine
from servicorn.core.engine.client.endpoints.api import router
from servicorn.core.engine.client.endpoints.middleware import register_jsonrpc_middleware


def create_client_app(
    *,
    client_engine: GrpcClientEngine | None = None,
    default_service_name: str = "gateway",
) -> FastAPI:
    """Create a FastAPI application that forwards JSON-RPC calls over gRPC."""
    engine = client_engine or GrpcClientEngine()
    app = FastAPI(title="servicorn client gateway", version="0.1.0")
    app.state.client_engine = engine
    app.state.default_service_name = default_service_name
    register_jsonrpc_middleware(app)
    app.include_router(router)
    return app
