import unittest

from servicorn.core.engine.server import ServicornEngine
from servicorn.core.grpc.v1 import gateway_pb2


def grpc_wsgi_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "application/json")])
    return [
        (
            b'{"path":"%s","method":"%s","trace_id":"%s"}'
            % (
                environ["PATH_INFO"].encode("utf-8"),
                environ["REQUEST_METHOD"].encode("utf-8"),
                environ.get("servicorn.context.trace_id", "").encode("utf-8"),
            )
        )
    ]


class ServerGrpcTests(unittest.TestCase):
    def test_handle_proto_request_returns_proto_response(self) -> None:
        engine = ServicornEngine("tests.test_server_grpc:grpc_wsgi_app")
        request = gateway_pb2.GrpcCallRequest(
            request=gateway_pb2.HttpRequest(
                http_method="POST",
                path="/grpc/server",
                query_string="id=9",
                headers=[gateway_pb2.Header(name="Content-Type", value="application/json")],
                body=b'{"ok":true}',
            ),
            context=gateway_pb2.RequestContext(trace_id="trace-server"),
        )
        response = engine.handle_proto_request(request)
        self.assertEqual(response.result.status_code, 200)
        self.assertEqual(response.result.headers[0].name, "Content-Type")
        self.assertIn(b'"path":"/grpc/server"', response.result.body)
        self.assertIn(b'"trace_id":"trace-server"', response.result.body)
