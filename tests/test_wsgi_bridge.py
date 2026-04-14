import unittest

from servicorn.core.engine.server.bridge import WSGIBridge
from servicorn.core.engine.common.models import NormalizedRequest, RequestContext


def sample_wsgi_app(environ, start_response):
    body = environ["wsgi.input"].read()
    response = {
        "path": environ["PATH_INFO"],
        "query": environ["QUERY_STRING"],
        "method": environ["REQUEST_METHOD"],
        "trace_id": environ.get("servicorn.context.trace_id"),
        "body": body.decode("utf-8"),
    }
    payload = (
        '{"path":"%s","query":"%s","method":"%s","trace_id":"%s","body":"%s"}'
        % (
            response["path"],
            response["query"],
            response["method"],
            response["trace_id"],
            response["body"].replace('"', '\\"'),
        )
    ).encode("utf-8")
    start_response("200 OK", [("Content-Type", "application/json")])
    return [payload]


class WSGIBridgeTests(unittest.TestCase):
    def test_bridge_maps_request_and_collects_response(self) -> None:
        bridge = WSGIBridge(sample_wsgi_app)
        request = NormalizedRequest(
            request_id="req-1",
            rpc_method="grpcCall",
            http_method="POST",
            path="/rpc/demo",
            query_string="id=7",
            headers=(("Content-Type", "application/json"),),
            body=b'{"ok":true}',
            context=RequestContext(trace_id="trace-1", caller="tester", timeout_ms=1000),
        )
        response = bridge.handle(request)
        self.assertEqual(response.request_id, "req-1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers, (("Content-Type", "application/json"),))
        self.assertIn(b'"path":"/rpc/demo"', response.body)
        self.assertIn(b'"query":"id=7"', response.body)
        self.assertIn(b'"trace_id":"trace-1"', response.body)
