"""Server runtime helpers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import grpc

from servicorn.core.engine.discovery import EtcdServiceDiscovery, ServiceEndpoint
from servicorn.core.engine.common.exceptions import RuntimeUnavailableError


class GatewayRuntime:
    """Runtime metadata and server lifecycle for the gateway gRPC backend."""

    name = "grpc"

    @classmethod
    def check_available(cls) -> None:
        try:
            import grpc  # noqa: F401
        except ModuleNotFoundError as exc:
            raise RuntimeUnavailableError(
                "gRPC runtime is not available in the active environment"
            ) from exc

    @classmethod
    def register_service(
        cls,
        service_name: str,
        host: str,
        port: int,
        discovery: EtcdServiceDiscovery | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Register this runtime endpoint in etcd."""
        registry = discovery or EtcdServiceDiscovery()
        endpoint = ServiceEndpoint(
            service_name=service_name,
            host=host,
            port=port,
            metadata=metadata or {"runtime": cls.name},
        )
        return registry.register(endpoint)

    @classmethod
    def serve(
        cls,
        *,
        host: str,
        port: int,
        wsgi_app: str,
        service_name: str = "gateway",
        register_service: bool = False,
        max_workers: int = 10,
        discovery: EtcdServiceDiscovery | None = None,
    ) -> None:
        """Start a blocking gRPC server for the Gateway service."""
        from servicorn.core.engine.server.engine import ServicornEngine
        from servicorn.core.engine.server.grpc import add_gateway_handler

        engine = ServicornEngine(wsgi_app=wsgi_app)
        server = grpc.server(ThreadPoolExecutor(max_workers=max_workers))
        add_gateway_handler(server, engine)
        bind_address = f"{host}:{port}"
        server.add_insecure_port(bind_address)
        discovery_key = None
        registry = discovery or EtcdServiceDiscovery()
        if register_service:
            discovery_key = cls.register_service(
                service_name=service_name,
                host=host,
                port=port,
                discovery=registry,
            )
        server.start()
        try:
            server.wait_for_termination()
        finally:
            if register_service and discovery_key:
                registry.unregister(service_name=service_name, host=host, port=port)
