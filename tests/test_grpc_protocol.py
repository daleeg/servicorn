import unittest

from servicorn.core.engine.client.models import JsonRpcRequest, JsonRpcResponse
from servicorn.core.engine.common.models import NormalizedResponse


class GrpcProtocolTests(unittest.TestCase):
    def test_protocol_parses_request(self) -> None:
        rpc_request = JsonRpcRequest.model_validate(
            {
                "jsonrpc": "2.0",
                "request_id": "req-grpc",
                "method": "grpcCall",
                "params": {
                    "request": {
                        "http_method": "POST",
                        "path": "/grpc/demo",
                        "headers": [["Content-Type", "application/json"]],
                        "body": {"ok": True},
                    },
                    "context": {"trace_id": "trace-grpc"},
                },
            }
        )
        request = rpc_request.to_normalized_request()
        self.assertEqual(request.request_id, "req-grpc")
        self.assertEqual(request.path, "/grpc/demo")
        self.assertEqual(request.body, b'{"ok":true}')

    def test_protocol_encodes_response(self) -> None:
        payload = JsonRpcResponse.from_normalized_response(
            NormalizedResponse(
                request_id="req-grpc",
                status_code=200,
                headers=(("Content-Type", "application/json"),),
                body=b'{"ok":true}',
            )
        ).model_dump(by_alias=True, exclude_none=True)
        self.assertEqual(payload["jsonrpc"], "2.0")
        self.assertEqual(payload["result"]["body"], {"ok": True})
