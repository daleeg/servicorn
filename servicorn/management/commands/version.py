"""Version command."""

from __future__ import annotations

import click

from servicorn import __version__

__all__ = ["version"]


@click.command()
@click.pass_context
def version(ctx) -> None:
    """Print the package version."""
    del ctx
    click.echo(__version__)
