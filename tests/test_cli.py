import unittest
from unittest.mock import patch

from click.testing import CliRunner

from servicorn.management.root import execute_from_command_line


class CliTests(unittest.TestCase):
    def test_version_command(self) -> None:
        runner = CliRunner()
        result = runner.invoke(execute_from_command_line, ["version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("0.1.0", result.output)

    def test_default_run_server_command_prints_runtime_plan(self) -> None:
        runner = CliRunner()
        with patch("servicorn.management.commands.run_server.GatewayRuntime.serve") as serve:
            result = runner.invoke(
                execute_from_command_line,
                ["--wsgi-app", "tests.test_engine:demo_wsgi_app", "--port", "9000"],
            )
        self.assertEqual(result.exit_code, 0)
        serve.assert_called_once()
        _, kwargs = serve.call_args
        self.assertEqual(kwargs["port"], 9000)
        self.assertEqual(kwargs["wsgi_app"], "tests.test_engine:demo_wsgi_app")

    def test_run_server_can_register_service(self) -> None:
        runner = CliRunner()
        with patch("servicorn.management.commands.run_server.GatewayRuntime.serve") as serve:
            result = runner.invoke(
                execute_from_command_line,
                ["run_server", "--register-service", "--workers", "20"],
            )
        self.assertEqual(result.exit_code, 0)
        _, kwargs = serve.call_args
        self.assertTrue(kwargs["register_service"])
        self.assertEqual(kwargs["service_name"], "gateway")
        self.assertEqual(kwargs["max_workers"], 20)

    def test_run_client_starts_uvicorn(self) -> None:
        runner = CliRunner()
        with patch("servicorn.management.commands.run_client.uvicorn.run") as run:
            result = runner.invoke(
                execute_from_command_line,
                [
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "8010",
                    "run_client",
                    "--service-name",
                    "gateway",
                    "--reload",
                    "--workers",
                    "2",
                    "--log-level",
                    "debug",
                ],
            )
        self.assertEqual(result.exit_code, 0)
        args, kwargs = run.call_args
        self.assertEqual(kwargs["host"], "0.0.0.0")
        self.assertEqual(kwargs["port"], 8010)
        self.assertTrue(kwargs["reload"])
        self.assertEqual(kwargs["workers"], 2)
        self.assertEqual(kwargs["log_level"], "debug")

    def test_run_server_loads_ini_configuration(self) -> None:
        runner = CliRunner()
        ini_content = "\n".join(
            [
                "[servicorn]",
                "host = 0.0.0.0",
                "port = 9100",
                "wsgi_app = tests.test_engine:demo_wsgi_app",
                "",
                "[server]",
                "service_name = ini-gateway",
                "register_service = true",
                "workers = 12",
                "",
                "[etcd]",
                "host = 10.1.1.10",
                "port = 32379",
                "protocol = http",
                "prefix = /custom/services",
            ]
        )
        with runner.isolated_filesystem():
            with open("servicorn.ini", "w", encoding="utf-8") as handle:
                handle.write(ini_content)
            with patch("servicorn.management.commands.run_server.GatewayRuntime.serve") as serve:
                result = runner.invoke(
                    execute_from_command_line,
                    ["--ini", "servicorn.ini", "run_server"],
                )
        self.assertEqual(result.exit_code, 0)
        _, kwargs = serve.call_args
        self.assertEqual(kwargs["host"], "0.0.0.0")
        self.assertEqual(kwargs["port"], 9100)
        self.assertEqual(kwargs["service_name"], "ini-gateway")
        self.assertTrue(kwargs["register_service"])
        self.assertEqual(kwargs["max_workers"], 12)
        self.assertEqual(kwargs["discovery"].host, "10.1.1.10")
        self.assertEqual(kwargs["discovery"].port, 32379)
        self.assertEqual(kwargs["discovery"].prefix, "/custom/services")

    def test_run_client_loads_ini_configuration(self) -> None:
        runner = CliRunner()
        ini_content = "\n".join(
            [
                "[servicorn]",
                "host = 0.0.0.0",
                "port = 8111",
                "",
                "[client]",
                "service_name = ini-gateway",
                "reload = true",
                "workers = 3",
                "log_level = warning",
                "",
                "[etcd]",
                "host = 10.1.1.20",
                "port = 42379",
                "protocol = http",
                "prefix = /client/services",
            ]
        )
        with runner.isolated_filesystem():
            with open("servicorn.ini", "w", encoding="utf-8") as handle:
                handle.write(ini_content)
            with patch("servicorn.management.commands.run_client.uvicorn.run") as run:
                result = runner.invoke(
                    execute_from_command_line,
                    ["--ini", "servicorn.ini", "run_client"],
                )
        self.assertEqual(result.exit_code, 0)
        _, kwargs = run.call_args
        self.assertEqual(kwargs["host"], "0.0.0.0")
        self.assertEqual(kwargs["port"], 8111)
        self.assertTrue(kwargs["reload"])
        self.assertEqual(kwargs["workers"], 3)
        self.assertEqual(kwargs["log_level"], "warning")

    @patch.dict(
        "os.environ",
        {
            "ETCD_HOST": "192.168.10.10",
            "ETCD_PORT": "52379",
            "ETCD_PROTOCOL": "https",
            "ETCD_PREFIX": "/env/services",
        },
        clear=False,
    )
    def test_run_server_loads_etcd_from_environment(self) -> None:
        runner = CliRunner()
        with patch("servicorn.management.commands.run_server.GatewayRuntime.serve") as serve:
            result = runner.invoke(execute_from_command_line, ["run_server"])
        self.assertEqual(result.exit_code, 0)
        _, kwargs = serve.call_args
        self.assertEqual(kwargs["discovery"].host, "192.168.10.10")
        self.assertEqual(kwargs["discovery"].port, 52379)
        self.assertEqual(kwargs["discovery"].protocol, "https")
        self.assertEqual(kwargs["discovery"].prefix, "/env/services")

    @patch.dict(
        "os.environ",
        {
            "ETCD_HOST": "192.168.20.10",
            "ETCD_PORT": "62379",
            "ETCD_PROTOCOL": "https",
            "ETCD_PREFIX": "/client/env/services",
        },
        clear=False,
    )
    def test_run_client_loads_etcd_from_environment(self) -> None:
        runner = CliRunner()
        with patch("servicorn.management.commands.run_client.create_client_app") as create_app:
            create_app.return_value = object()
            with patch("servicorn.management.commands.run_client.uvicorn.run") as run:
                result = runner.invoke(execute_from_command_line, ["run_client"])
        self.assertEqual(result.exit_code, 0)
        _, create_kwargs = create_app.call_args
        discovery = create_kwargs["client_engine"].discovery
        self.assertEqual(discovery.host, "192.168.20.10")
        self.assertEqual(discovery.port, 62379)
        self.assertEqual(discovery.protocol, "https")
        self.assertEqual(discovery.prefix, "/client/env/services")
        run.assert_called_once()
