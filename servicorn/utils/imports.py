"""Import helpers with no internal package dependencies."""

from __future__ import annotations

import importlib


def import_string(import_path: str) -> object:
    """Import an object from a ``module:attr`` path."""
    module_name, separator, attribute_name = import_path.partition(":")
    if not separator or not module_name or not attribute_name:
        raise ValueError("import path must use the format 'module:attribute'")
    module = importlib.import_module(module_name)
    return getattr(module, attribute_name)
