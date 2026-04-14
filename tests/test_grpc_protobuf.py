import unittest

from servicorn.core.engine.common.models import NormalizedRequest, NormalizedResponse
from servicorn.core.grpc.v1 import gateway_pb2


class GrpcProtobufTests(unittest.TestCase):
    def test_request_from_proto(self) -> None:
        proto_request = gateway_pb2.GrpcCallRequest(
            request=gateway_pb2.HttpRequest(
                http_method="POST",
                path="/proto/demo",
                query_string="id=1",
                headers=[gateway_pb2.Header(name="Content-Type", value="application/json")],
                body=b'{"ok":true}',
            ),
            context=gateway_pb2.RequestContext(
                trace_id="trace-proto",
                caller="tester",
                timeout_ms=1500,
                extras={"tenant": "prod"},
            ),
        )
        request = NormalizedRequest.from_grpc_call_request(proto_request)
        self.assertEqual(request.request_id, "")
        self.assertEqual(request.rpc_method, "GrpcCall")
        self.assertEqual(request.path, "/proto/demo")
        self.assertEqual(request.query_string, "id=1")
        self.assertEqual(request.context.extras["tenant"], "prod")

    def test_response_to_proto(self) -> None:
        response = NormalizedResponse(
            request_id="req-proto",
            status_code=200,
            headers=(("Content-Type", "application/json"),),
            body=b'{"ok":true}',
        )
        proto_response = response.to_grpc_call_response()
        self.assertEqual(proto_response.result.status_code, 200)
        self.assertEqual(proto_response.result.headers[0].name, "Content-Type")
