# servicorn

`servicorn` 是一个面向 Django `WSGI` 应用的网关式启动器，当前通过 gRPC 作为服务端传输协议运行，并提供两类入口：

- `run_server`：启动 gRPC 网关服务端，把 `GrpcCall` 请求转给 Django/WSGI 应用
- `run_client`：启动基于 FastAPI 的 JSON-RPC 网关，把 JSON-RPC 请求转发到 gRPC 服务端

当前实现聚焦于一条主链路：

`JSON-RPC -> gRPC -> WSGI -> Django`

## 安装

本仓库默认使用 `/opt/venv/servicorn` 作为 Python 虚拟环境。

安装运行和测试依赖：

```bash
/opt/venv/servicorn/bin/python -m pip install -e .[tests]
```

如果只安装运行时依赖：

```bash
/opt/venv/servicorn/bin/python -m pip install -e .
```

## 使用方式

查看版本：

```bash
/opt/venv/servicorn/bin/python manage.py version
```

启动 gRPC 网关服务端，并加载 Django/WSGI 应用：

```bash
/opt/venv/servicorn/bin/python manage.py \
  --host 127.0.0.1 \
  --port 50051 \
  --wsgi-app lucifer.wsgi:application \
  run_server
```

启动 JSON-RPC 客户端网关：

```bash
/opt/venv/servicorn/bin/python manage.py \
  --host 127.0.0.1 \
  --port 8010 \
  run_client
```

`run_client` 常用参数：

- `--service-name`
- `--reload`
- `--workers`
- `--log-level`

`run_server` 常用参数：

- `--service-name`
- `--register-service`
- `--workers`

## INI 配置

`run_server` 和 `run_client` 都支持通过 `--ini` 加载配置，优先级为：

`CLI > 环境变量 > ini > 默认值`

示例：

```ini
[servicorn]
host = 127.0.0.1

[server]
port = 50051
wsgi_app = lucifer.wsgi:application
service_name = gateway
register_service = true
workers = 10

[client]
port = 8010
service_name = gateway
reload = false
workers = 1
log_level = info

[etcd]
host = 127.0.0.1
port = 2379
protocol = http
prefix = /servicorn/services
```

使用方式：

```bash
/opt/venv/servicorn/bin/python manage.py --ini servicorn.ini run_server
/opt/venv/servicorn/bin/python manage.py --ini servicorn.ini run_client
```

`[etcd]` 配置由 `run_server` 和 `run_client` 共用，也可以通过环境变量覆盖：

- `ETCD_HOST`
- `ETCD_PORT`
- `ETCD_PROTOCOL`
- `ETCD_PREFIX`

## 测试

运行当前测试集：

```bash
/opt/venv/servicorn/bin/python -m unittest discover -s tests -v
```
