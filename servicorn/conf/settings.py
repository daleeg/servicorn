"""Default settings for servicorn."""

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_WSGI_APP = "tests.test_engine:demo_wsgi_app"

ETCD = {
    "host": "127.0.0.1",
    "port": 2379,
    "protocol": "http",
    "prefix": "/servicorn/services",
}

SERVER = {
    "host": DEFAULT_HOST,
    "port": DEFAULT_PORT,
    "wsgi_app": DEFAULT_WSGI_APP,
    "service_name": "gateway",
    "register_service": False,
    "workers": 10,
}

CLIENT = {
    "host": DEFAULT_HOST,
    "port": 8010,
    "wsgi_app": DEFAULT_WSGI_APP,
    "service_name": "gateway",
    "reload": False,
    "workers": 1,
    "log_level": "info",
}
