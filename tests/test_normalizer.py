import unittest

from servicorn.core.engine.client.models import JsonRpcRequest


class NormalizeMessageTests(unittest.TestCase):
    def test_structured_request_is_normalized_for_wsgi(self) -> None:
        rpc_request = JsonRpcRequest.model_validate(
            {
                "jsonrpc": "2.0",
                "request_id": "req-123",
                "method": "grpcCall",
                "params": {
                    "request": {
                        "http_method": "post",
                        "path": "/user/profile/get",
                        "query": {"id": "1001", "tag": ["a", "b"]},
                        "headers": [
                            ["Authorization", "Bearer xxx"],
                            ["Content-Type", "application/json"],
                        ],
                        "body": {"with_extra": True},
                    },
                    "context": {
                        "trace_id": "trace-abc",
                        "caller": "api-gateway",
                        "timeout_ms": 3000,
                        "tenant": "prod",
                    },
                },
            }
        )
        request = rpc_request.to_normalized_request()
        self.assertEqual(request.request_id, "req-123")
        self.assertEqual(request.rpc_method, "grpcCall")
        self.assertEqual(request.http_method, "POST")
        self.assertEqual(request.path, "/user/profile/get")
        self.assertEqual(request.query_string, "id=1001&tag=a&tag=b")
        self.assertEqual(request.body, b'{"with_extra":true}')
        self.assertEqual(request.context.trace_id, "trace-abc")
        self.assertEqual(request.context.extras["tenant"], "prod")
