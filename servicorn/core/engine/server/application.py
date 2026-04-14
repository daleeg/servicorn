"""Application loading helpers."""

from __future__ import annotations

from collections.abc import Callable

from servicorn.core.engine.common.exceptions import ConfigurationError
from servicorn.log import get_logger
from servicorn.utils.imports import import_string

WSGIApplication = Callable[[dict, Callable], object]
LOG = get_logger(__name__)


def load_wsgi_application(import_path: str) -> WSGIApplication:
    """Load a WSGI application from a ``module:attr`` import path."""
    LOG.debug("loading wsgi application import_path=%s", import_path)
    application = import_string(import_path)
    if not callable(application):
        raise ConfigurationError(f"WSGI application '{import_path}' is not callable")
    LOG.debug("loaded wsgi application import_path=%s", import_path)
    return application
