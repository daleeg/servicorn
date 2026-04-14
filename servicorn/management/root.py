"""Root command group for servicorn management commands."""

from __future__ import annotations

from importlib import import_module

import click
from click.core import Context

from servicorn.conf import settings
from servicorn.utils.config import IniConfig, resolve_option
from servicorn.utils.imports import import_string

ROOT_MODULE = "servicorn.management.commands"


class RootGroup(click.Group):
    """Group that loads command modules from ``servicorn.management.commands``."""

    def __init__(self, name=None, commands=None, **attrs):
        super().__init__(name=name, commands=commands, **attrs)
        self.commands.update(self.load_commands())

    @classmethod
    def load_commands(cls) -> dict[str, click.Command]:
        commands: dict[str, click.Command] = {}
        sub_commands = import_module(ROOT_MODULE).COMMANDS
        for sub_command in sub_commands:
            module_str = f"{ROOT_MODULE}.{sub_command}"
            mod = import_module(module_str)
            for cmd_name in mod.__all__:
                obj = getattr(mod, cmd_name)
                if isinstance(obj, click.Command):
                    commands[cmd_name] = obj
        return commands


@click.group(invoke_without_command=True, cls=RootGroup)
@click.option("--ini", "ini_path", type=click.Path(exists=True, dir_okay=False, path_type=str))
@click.option("-H", "--host", envvar="HOST", default=None)
@click.option("-P", "--port", envvar="PORT", default=None, type=int)
@click.option(
    "--wsgi-app",
    envvar="WSGI_APP",
    default=None,
    help="WSGI app import path, e.g. package.module:app",
)
@click.pass_context
def execute_from_command_line(ctx: Context, ini_path: str | None, host: str | None, port: int | None, wsgi_app: str | None) -> None:
    """Root command entrypoint that stores shared options on ``ctx.obj``."""
    subcommand = ctx.invoked_subcommand or "run_server"
    command_section = "client" if subcommand == "run_client" else "server"
    config = IniConfig.load(ini_path)
    section_defaults = settings.CLIENT if command_section == "client" else settings.SERVER

    ctx.ensure_object(dict)
    ctx.obj.update(
        {
            "settings": settings,
            "ini_path": ini_path,
            "config": config,
            "config_section": command_section,
            "host": resolve_option(
                host,
                config.get_str("servicorn", "host"),
                config.get_str(command_section, "host"),
                section_defaults["host"],
            ),
            "port": resolve_option(
                port,
                config.get_int("servicorn", "port"),
                config.get_int(command_section, "port"),
                section_defaults["port"],
            ),
            "wsgi_app": resolve_option(
                wsgi_app,
                config.get_str("servicorn", "wsgi_app"),
                config.get_str(command_section, "wsgi_app"),
                section_defaults["wsgi_app"],
            ),
        }
    )
    if ctx.invoked_subcommand is None:
        from servicorn.management.commands.run_server import run_server

        ctx.invoke(run_server)
