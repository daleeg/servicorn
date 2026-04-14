"""Run the FastAPI JSON-RPC client gateway."""

from __future__ import annotations

import click
import uvicorn

from servicorn.conf import settings
from servicorn.core.engine import EtcdServiceDiscovery, GrpcClientEngine
from servicorn.core.engine.client import create_client_app
from servicorn.utils.config import resolve_option

__all__ = ["run_client"]


@click.command()
@click.option(
    "--service-name",
    envvar="GRPC_SERVICE_NAME",
    default=None,
    help="Service name used for gRPC service discovery.",
)
@click.option(
    "--reload/--no-reload",
    envvar="CLIENT_RELOAD",
    default=None,
    help="Enable uvicorn auto reload for client development.",
)
@click.option(
    "--workers",
    envvar="CLIENT_WORKERS",
    default=None,
    type=int,
    help="Number of uvicorn worker processes.",
)
@click.option(
    "--log-level",
    envvar="CLIENT_LOG_LEVEL",
    default=None,
    type=click.Choice(["critical", "error", "warning", "info", "debug", "trace"], case_sensitive=False),
    help="Uvicorn log level.",
)
@click.pass_context
def run_client(
    ctx,
    service_name: str | None,
    reload: bool | None,
    workers: int | None,
    log_level: str | None,
) -> None:
    """Start the FastAPI client gateway."""
    config = ctx.obj["config"]
    service_name = resolve_option(
        service_name,
        config.get_str("client", "service_name"),
        settings.CLIENT["service_name"],
    )
    reload = resolve_option(
        reload,
        config.get_bool("client", "reload"),
        settings.CLIENT["reload"],
    )
    workers = resolve_option(
        workers,
        config.get_int("client", "workers"),
        settings.CLIENT["workers"],
    )
    log_level = resolve_option(
        log_level,
        config.get_str("client", "log_level"),
        settings.CLIENT["log_level"],
    )
    discovery = EtcdServiceDiscovery.from_config(config)
    app = create_client_app(
        client_engine=GrpcClientEngine(discovery=discovery),
        default_service_name=service_name,
    )
    uvicorn.run(
        app,
        host=ctx.obj["host"],
        port=ctx.obj["port"],
        reload=reload,
        workers=workers,
        log_level=log_level.lower(),
    )
