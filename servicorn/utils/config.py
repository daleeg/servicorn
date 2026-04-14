"""INI configuration loading helpers."""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path


class IniConfig:
    """Wrapper around ``ConfigParser`` with typed access helpers."""

    def __init__(self, parser: ConfigParser):
        self.parser = parser

    @classmethod
    def load(cls, path: str | None) -> "IniConfig":
        parser = ConfigParser()
        if path:
            parser.read(Path(path).expanduser())
        return cls(parser)

    def get_str(self, section: str, option: str) -> str | None:
        if self.parser.has_option(section, option):
            return self.parser.get(section, option)
        return None

    def get_int(self, section: str, option: str) -> int | None:
        value = self.get_str(section, option)
        if value is None:
            return None
        return int(value)

    def get_bool(self, section: str, option: str) -> bool | None:
        if self.parser.has_option(section, option):
            return self.parser.getboolean(section, option)
        return None


def resolve_option(*values):
    """Return the first non-``None`` value from left to right."""
    for value in values:
        if value is not None:
            return value
    return None
