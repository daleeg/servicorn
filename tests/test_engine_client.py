import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from servicorn.core.engine.client import GrpcClientEngine, create_client_app
from servicorn.core.engine.client.models import RpcHttpRequest
from servicorn.core.engine.client.endpoints import GATEWAY_RPC_PATH
from servicorn.core.engine.client.engine import GRPC_CHANNEL_OPTIONS
from servicorn.core.engine.common.models import NormalizedRequest
from servicorn.core.engine.discovery import EtcdServiceDiscovery, ServiceEndpoint
from servicorn.core.grpc.v1 import gateway_pb2


class FakeEtcdClient:
    def __init__(self):
        self.values = {}

    def put(self, key, value):
        self.values[key] = value

    def get_prefix(self, prefix):
        for key, value in self.values.items():
            if key.startswith(prefix):
                yield value, {"key": key}


def fake_grpc_caller(target, proto_request):
    del target
    return gateway_pb2.GrpcCallResponse(
        result=gateway_pb2.ResponseResult(
            status_code=200,
            headers=[gateway_pb2.Header(name="Content-Type", value="application/json")],
            body=(
                b'{"path":"%s","method":"%s","trace_id":"%s"}'
                % (
                    proto_request.request.path.encode("utf-8"),
                    proto_request.request.http_method.encode("utf-8"),
                    proto_request.context.trace_id.encode("utf-8"),
                )
            ),
        )
    )


class EngineClientTests(unittest.TestCase):
    def setUp(self) -> None:
        fake_etcd = FakeEtcdClient()
        discovery = EtcdServiceDiscovery(client=fake_etcd)
        discovery.register(ServiceEndpoint(service_name="gateway", host="127.0.0.1", port=50051))
        self.engine = GrpcClientEngine(discovery=discovery, grpc_caller=fake_grpc_caller)

    def test_client_engine_forwards_rpc_to_grpc(self) -> None:
        response = self.engine.forward_rpc(
            "grpcCall",
            RpcHttpRequest(
                http_method="POST",
                path="/client/demo",
                headers=[["Content-Type", "application/json"]],
                body={"ok": True},
                context={"trace_id": "trace-client"},
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["path"], "/client/demo")

    def test_fastapi_app_exposes_gateway_rpc_endpoint(self) -> None:
        app = create_client_app(client_engine=self.engine)
        client = TestClient(app)
        response = client.post(
            GATEWAY_RPC_PATH,
            json={
                "jsonrpc": "2.0",
                "request_id": "req-api",
                "method": "grpcCall",
                "params": {
                    "request": {
                        "http_method": "POST",
                        "path": "/api/demo",
                        "headers": [["Content-Type", "application/json"]],
                        "body": {"ok": True},
                    },
                    "context": {"trace_id": "trace-api"},
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["request_id"], "req-api")
        self.assertEqual(payload["result"]["body"]["trace_id"], "trace-api")

    def test_default_grpc_caller_disables_http_proxy(self) -> None:
        proto_response = gateway_pb2.GrpcCallResponse(
            result=gateway_pb2.ResponseResult(status_code=200)
        )
        method = MagicMock(return_value=proto_response)
        channel = MagicMock()
        channel.__enter__.return_value = channel
        channel.unary_unary.return_value = method
        normalized_request = NormalizedRequest(
            request_id="req-default",
            rpc_method="grpcCall",
            request={
                "http_method": "GET",
                "path": "/default",
                "query_string": "",
                "headers": (),
                "body": b"",
            },
        )

        with patch("servicorn.core.engine.client.engine.grpc.insecure_channel", return_value=channel) as insecure_channel:
            response = GrpcClientEngine._default_grpc_caller("127.0.0.1:50051", normalized_request)

        insecure_channel.assert_called_once_with("127.0.0.1:50051", options=GRPC_CHANNEL_OPTIONS)
        channel.unary_unary.assert_called_once()
        method.assert_called_once()
        proto_request = method.call_args.args[0]
        self.assertEqual(proto_request.request.path, "/default")
        self.assertEqual(response, proto_response)

    def test_grpc_json_call_converts_normalized_request_and_response(self) -> None:
        normalized_request = NormalizedRequest(
            request_id="req-json",
            rpc_method="grpcCall",
            request={
                "http_method": "POST",
                "path": "/json",
                "query_string": "",
                "headers": (("Content-Type", "application/json"),),
                "body": b'{"ok":true}',
            },
        )

        normalized_response = self.engine.grpc_json_call("127.0.0.1:50051", normalized_request)

        self.assertEqual(normalized_response.request_id, "req-json")
        self.assertEqual(normalized_response.status_code, 200)
