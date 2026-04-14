"""Client-side engine package."""

__all__ = ["GrpcClientEngine", "JsonRpcRequest", "JsonRpcResponse", "create_client_app"]


def __getattr__(name: str):
    if name == "GrpcClientEngine":
        from servicorn.core.engine.client import engine

        return engine.GrpcClientEngine
    if name == "create_client_app":
        from servicorn.core.engine.client.endpoints import app

        return app.create_client_app
    if name in {"JsonRpcRequest", "JsonRpcResponse"}:
        from servicorn.core.engine.client import models

        return getattr(models, name)
    raise AttributeError(name)
