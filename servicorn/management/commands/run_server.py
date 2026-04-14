"""Runtime planning command."""

from __future__ import annotations

import click

from servicorn.core.engine import EtcdServiceDiscovery, GatewayRuntime
from servicorn.conf import settings
from servicorn.utils.config import resolve_option

__all__ = ["run_server"]


@click.command()
@click.option(
    "--service-name",
    envvar="SERVICE_NAME",
    default=None,
    help="Service name to use when registering in discovery.",
)
@click.option(
    "--register-service/--no-register-service",
    default=None,
    help="Register the gateway server in etcd service discovery.",
)
@click.option(
    "--workers",
    envvar="SERVER_WORKERS",
    default=None,
    type=int,
    help="Maximum gRPC worker threads.",
)
@click.pass_context
def run_server(ctx, service_name: str | None, register_service: bool | None, workers: int | None) -> None:
    """Start the blocking gateway gRPC server."""
    config = ctx.obj["config"]
    service_name = resolve_option(
        service_name,
        config.get_str("server", "service_name"),
        settings.SERVER["service_name"],
    )
    register_service = resolve_option(
        register_service,
        config.get_bool("server", "register_service"),
        settings.SERVER["register_service"],
    )
    workers = resolve_option(
        workers,
        config.get_int("server", "workers"),
        settings.SERVER["workers"],
    )
    discovery = EtcdServiceDiscovery.from_config(config)
    GatewayRuntime.serve(
        host=ctx.obj["host"],
        port=ctx.obj["port"],
        wsgi_app=ctx.obj["wsgi_app"],
        service_name=service_name,
        register_service=register_service,
        max_workers=workers,
        discovery=discovery,
    )
