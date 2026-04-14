"""Service discovery abstractions for engine components."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

from pydantic import Field

from servicorn.conf import settings
from servicorn.core.engine.common.exceptions import RuntimeUnavailableError
from servicorn.core.engine.common.models import FrozenModel
from servicorn.utils.config import resolve_option
from servicorn.utils.json import json_dumps, json_loads

if TYPE_CHECKING:
    from servicorn.utils.config import IniConfig


class ServiceEndpoint(FrozenModel):
    """A resolved service endpoint."""

    service_name: str
    host: str
    port: int
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


def _coerce_version_tuple(value: str) -> tuple[int, ...]:
    parts = []
    for part in str(value).split("."):
        digits = "".join(char for char in part if char.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts or [0])


class EtcdServiceDiscovery:
    """Minimal etcd-backed service discovery adapter."""

    def __init__(
        self,
        prefix: str = "/servicorn/services",
        client=None,
        host: str = "127.0.0.1",
        port: int = 2379,
        protocol: str = "http",
    ):
        self.prefix = prefix.rstrip("/")
        self._client = client
        self.host = host
        self.port = port
        self.protocol = protocol

    @classmethod
    def from_config(cls, config: "IniConfig", client=None) -> "EtcdServiceDiscovery":
        return cls(
            client=client,
            host=resolve_option(
                os.getenv("ETCD_HOST"),
                config.get_str("etcd", "host"),
                settings.ETCD["host"],
            ),
            port=resolve_option(
                _get_env_int("ETCD_PORT"),
                config.get_int("etcd", "port"),
                settings.ETCD["port"],
            ),
            protocol=resolve_option(
                os.getenv("ETCD_PROTOCOL"),
                config.get_str("etcd", "protocol"),
                settings.ETCD["protocol"],
            ),
            prefix=resolve_option(
                os.getenv("ETCD_PREFIX"),
                config.get_str("etcd", "prefix"),
                settings.ETCD["prefix"],
            ),
        )

    @property
    def client(self):
        if self._client is None:
            self._client = self._create_default_client()
        return self._client

    def register(self, endpoint: ServiceEndpoint) -> str:
        """Register a service endpoint in etcd."""
        key = self._service_key(endpoint.service_name, endpoint.address)
        self.client.put(key, json_dumps(endpoint.model_dump()))
        return key

    def unregister(self, service_name: str, host: str, port: int) -> None:
        """Remove a registered service endpoint."""
        self.client.delete(self._service_key(service_name, f"{host}:{port}"))

    def resolve(self, service_name: str) -> ServiceEndpoint | None:
        """Resolve the first service endpoint stored for a service name."""
        prefix = f"{self.prefix}/{service_name}/"
        client = self.client
        if hasattr(client, "range"):
            response = client.range(prefix, prefix=True)
            for item in getattr(response, "kvs", ()):
                raw_value = getattr(item, "value", b"")
                value = raw_value.decode("utf-8") if isinstance(raw_value, bytes) else str(raw_value)
                return ServiceEndpoint.model_validate(json_loads(value))
        elif hasattr(client, "get_prefix"):
            for raw_value, _metadata in client.get_prefix(prefix):
                value = raw_value.decode("utf-8") if isinstance(raw_value, bytes) else str(raw_value)
                return ServiceEndpoint.model_validate(json_loads(value))
        return None

    def _service_key(self, service_name: str, address: str) -> str:
        return f"{self.prefix}/{service_name}/{address}"

    @contextmanager
    def _direct_client_environment(self):
        previous = {
            "HTTP_PROXY": os.environ.get("HTTP_PROXY"),
            "HTTPS_PROXY": os.environ.get("HTTPS_PROXY"),
            "ALL_PROXY": os.environ.get("ALL_PROXY"),
            "http_proxy": os.environ.get("http_proxy"),
            "https_proxy": os.environ.get("https_proxy"),
            "all_proxy": os.environ.get("all_proxy"),
            "NO_PROXY": os.environ.get("NO_PROXY"),
            "no_proxy": os.environ.get("no_proxy"),
        }
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("ALL_PROXY", None)
        os.environ.pop("http_proxy", None)
        os.environ.pop("https_proxy", None)
        os.environ.pop("all_proxy", None)
        os.environ["NO_PROXY"] = "*"
        os.environ["no_proxy"] = "*"
        try:
            yield
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def _create_default_client(self):
        try:
            import etcd3
        except ModuleNotFoundError as exc:
            raise RuntimeUnavailableError(
                "etcd3-py is not available in the active environment"
            ) from exc
        with self._direct_client_environment():
            client = etcd3.client(
                host=self.host,
                port=self.port,
            )
        if getattr(client, "server_version", None) and not hasattr(client, "server_version_sem"):
            client.server_version_sem = _coerce_version_tuple(client.server_version)
        if getattr(client, "cluster_version", None) and not hasattr(client, "cluster_version_sem"):
            client.cluster_version_sem = _coerce_version_tuple(client.cluster_version)
        session = getattr(client, "_session", None)
        if session is not None:
            session.trust_env = False
        return client


def _get_env_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None:
        return None
    return int(value)
