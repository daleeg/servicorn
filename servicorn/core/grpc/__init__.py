"""gRPC-style protocol helpers for servicorn."""

__all__ = [
    "v1",
]


def __getattr__(name: str):
    if name == "v1":
        from servicorn.core.grpc import v1

        return v1
    raise AttributeError(name)
