"""JSON helpers with a stable, compact encoding policy."""

from __future__ import annotations

from typing import Any

import orjson


_PRETTY_OPTIONS = orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS
_COMPACT_OPTIONS = orjson.OPT_SORT_KEYS


def json_dumps(value: object, *, pretty: bool = False) -> str:
    """Dump JSON using ``orjson`` with UTF-8 output."""
    option = _PRETTY_OPTIONS if pretty else _COMPACT_OPTIONS
    return orjson.dumps(value, option=option).decode("utf-8")


def json_loads(value: str | bytes | bytearray) -> Any:
    """Load JSON text or bytes using ``orjson``."""
    return orjson.loads(value)
