"""HTTP-oriented utility helpers with no internal package dependencies."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from urllib.parse import urlencode

from servicorn.utils.json import json_dumps


def normalize_headers(value: object) -> tuple[tuple[str, str], ...]:
    """Normalize incoming headers into a tuple of ``(name, value)`` pairs."""
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return tuple((str(name), str(current)) for name, current in value.items())
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        headers: list[tuple[str, str]] = []
        for item in value:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError("headers entries must be [name, value] pairs")
            headers.append((str(item[0]), str(item[1])))
        return tuple(headers)
    raise ValueError("headers must be a mapping or a sequence of pairs")


def normalize_query_string(query_string: object, query: object) -> str:
    """Prefer an explicit query string, otherwise encode a structured query."""
    if query_string not in (None, ""):
        return str(query_string)
    if query in (None, "", {}):
        return ""
    if not isinstance(query, Mapping):
        raise ValueError("query must be an object when query_string is absent")
    items: list[tuple[str, object]] = []
    for key, value in query.items():
        if isinstance(value, list):
            items.extend((str(key), item) for item in value)
        else:
            items.append((str(key), value))
    return urlencode(items, doseq=True)


def encode_body(body: object) -> bytes:
    """Encode a structured body into bytes for WSGI transport."""
    if body is None:
        return b""
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode("utf-8")
    if isinstance(body, (dict, list, tuple, int, float, bool)):
        return json_dumps(body).encode("utf-8")
    raise ValueError("body must be bytes, text, or JSON-serializable data")


def normalize_path(path: object) -> str:
    """Ensure the request path is a non-empty absolute path."""
    normalized = str(path or "/")
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized
