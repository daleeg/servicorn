"""Core engine package for servicorn."""

__all__ = ["ServicornEngine", "GrpcClientEngine", "GatewayRuntime", "EtcdServiceDiscovery"]


def __getattr__(name: str):
    if name == "ServicornEngine":
        from servicorn.core.engine import ServicornEngine

        return ServicornEngine
    if name == "GrpcClientEngine":
        from servicorn.core.engine import GrpcClientEngine

        return GrpcClientEngine
    if name == "GatewayRuntime":
        from servicorn.core.engine import GatewayRuntime

        return GatewayRuntime
    if name == "EtcdServiceDiscovery":
        from servicorn.core.engine import EtcdServiceDiscovery

        return EtcdServiceDiscovery
    raise AttributeError(name)
