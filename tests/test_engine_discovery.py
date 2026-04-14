import unittest

from servicorn.core.engine.client import GrpcClientEngine
from servicorn.core.engine.discovery import EtcdServiceDiscovery, ServiceEndpoint
from servicorn.core.engine.server import GatewayRuntime


class FakeEtcdClient:
    def __init__(self):
        self.values = {}

    def put(self, key, value):
        self.values[key] = value

    def delete(self, key):
        self.values.pop(key, None)

    def get_prefix(self, prefix):
        for key, value in self.values.items():
            if key.startswith(prefix):
                yield value, {"key": key}


class EngineDiscoveryTests(unittest.TestCase):
    def test_register_and_resolve_service(self) -> None:
        discovery = EtcdServiceDiscovery(client=FakeEtcdClient())
        key = GatewayRuntime.register_service(
            service_name="gateway",
            host="127.0.0.1",
            port=9000,
            discovery=discovery,
        )
        self.assertIn("/servicorn/services/gateway/127.0.0.1:9000", key)
        endpoint = discovery.resolve("gateway")
        self.assertIsNotNone(endpoint)
        self.assertEqual(endpoint.address, "127.0.0.1:9000")

    def test_client_engine_builds_target_from_discovery(self) -> None:
        fake_client = FakeEtcdClient()
        discovery = EtcdServiceDiscovery(client=fake_client)
        discovery.register(
            ServiceEndpoint(
                service_name="gateway",
                host="10.0.0.2",
                port=7001,
                metadata={"version": "v1"},
            )
        )
        engine = GrpcClientEngine(discovery=discovery)
        self.assertEqual(engine.build_target("gateway"), "10.0.0.2:7001")
