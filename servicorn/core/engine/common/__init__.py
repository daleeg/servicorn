"""Common engine components shared by client and server flows."""

__all__ = [
    "ConfigurationError",
    "ErrorInfo",
    "FrozenModel",
    "HttpHeader",
    "HttpRequest",
    "HttpResponse",
    "InvalidRequestError",
    "NormalizedRequest",
    "NormalizedResponse",
    "RequestContext",
    "RuntimeUnavailableError",
    "ServicornError",
]


def __getattr__(name: str):
    if name in {
        "ErrorInfo",
        "FrozenModel",
        "HttpHeader",
        "HttpRequest",
        "HttpResponse",
        "NormalizedRequest",
        "NormalizedResponse",
        "RequestContext",
    }:
        from servicorn.core.engine.common import models

        return getattr(models, name)
    if name in {
        "ConfigurationError",
        "InvalidRequestError",
        "RuntimeUnavailableError",
        "ServicornError",
    }:
        from servicorn.core.engine.common import exceptions

        return getattr(exceptions, name)
    raise AttributeError(name)
