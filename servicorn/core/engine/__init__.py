"""Engine package for client, server, and service discovery flows."""

__all__ = [
    "EtcdServiceDiscovery",
    "GatewayRuntime",
    "GrpcClientEngine",
    "ServiceEndpoint",
    "ServicornEngine",
    "create_client_app",
]


def __getattr__(name: str):
    if name in {"GrpcClientEngine", "create_client_app"}:
        from servicorn.core.engine import client

        return getattr(client, name)
    if name in {"EtcdServiceDiscovery", "ServiceEndpoint"}:
        from servicorn.core.engine import discovery

        return getattr(discovery, name)
    if name in {"GatewayRuntime", "ServicornEngine"}:
        from servicorn.core.engine import server

        return getattr(server, name)
    raise AttributeError(name)
