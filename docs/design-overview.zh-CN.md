# Servicorn 设计概览

## 1. 项目目标

`servicorn` 的目标是以接近 `daphne` 的服务运行方式启动 Django 应用，并优先支持一种 gRPC 风格的 RPC 协议。

第一阶段 **不考虑 ASGI**，主要执行目标是现有 Django 的 **WSGI** 应用。

当前核心思路是：

- 客户端通过结构化 RPC 接口发起调用；
- 服务端接收并解析标准化后的 RPC 请求；
- 请求被转换为 WSGI 请求；
- Django 继续使用现有路由、中间件和视图栈处理请求；
- 最终响应再被封装回 RPC 响应返回给客户端。

## 2. 当前定位

本项目 **不是** 一个标准的 gRPC 业务服务实现。

当前定位是：

- 服务运行时尽量参考 `daphne`；
- 传输语义借鉴 gRPC / HTTP2；
- 请求模型尽量接近 HTTP/1 的请求语义；
- Django 集成方式采用 WSGI；
- protobuf 作为优先采用的原生消息定义方式。

换句话说，它更接近一个 **面向 Django 的 RPC-to-WSGI 网关服务器**，而不是传统意义上的 gRPC 应用服务器。

## 3. 协议方向

### 3.1 对外客户端接口

客户端对外可以继续保持结构化、易用的 JSON-RPC 风格：

- `jsonrpc`
- `id`
- `method`
- `params.request`
- `params.context`

这一层允许：

- `query` 采用结构化对象；
- `body` 采用结构化对象；
- 由 SDK 负责标准化和编码。

### 3.2 内部传输请求

真正进入传输层之前，请求应被标准化为接近 HTTP 的统一请求模型：

- `http_method`
- `path`
- `query_string`
- `headers`
- `body`
- `context`

当前已达成的设计约束：

- `headers` 要保留 HTTP 语义，并支持重复值；
- `query` 需要在发送前转换成 `query_string`；
- `body` 需要在发送前完成编码；
- 服务端接收的是标准化请求，而不是结构化对象与原始载荷混合的请求。

## 4. 消息编码

当前更倾向于使用 **protobuf message**，但不在第一阶段直接绑定标准 gRPC `service` 定义。

也就是说：

- 用 protobuf 定义稳定的请求/响应结构；
- 第一阶段不依赖标准 gRPC 的 `service` / `rpc` 模型；
- 以 protobuf `message` 作为传输契约；
- 协议语义由项目自身控制。

这样做的好处是：

- 消息结构强约束；
- 便于未来支持多语言客户端；
- 适合二进制载荷；
- 减少服务端在进入 WSGI 前的额外重组成本。

## 5. 服务端架构

当前服务端建议拆成四个核心模块。

### 5.1 Runtime

建议基于 **Twisted** 实现。

职责：

- 监听和绑定；
- 连接生命周期管理；
- 超时控制；
- TLS 以及未来对 socket / fd 的支持；
- 优雅退出；
- 基础日志和运行时控制。

这一层不处理 Django 业务逻辑。

### 5.2 RPC Protocol

职责：

- 接收并解析 RPC 请求；
- 校验消息 envelope 和请求结构；
- 解码 protobuf 或其他传输消息；
- 输出统一的内部标准化请求对象。

这一层不直接构造 WSGI。

### 5.3 WSGI Bridge

这是当前设计中的核心模块。

职责：

- 将标准化 RPC 请求转换成 WSGI `environ`；
- 把请求上下文映射到 header 或自定义 environ 字段；
- 加载并调用 Django WSGI application；
- 收集应用返回的状态码、响应头和响应体。

典型映射包括：

- `http_method -> REQUEST_METHOD`
- `path -> PATH_INFO`
- `query_string -> QUERY_STRING`
- `body -> wsgi.input`
- `headers -> HTTP_* / CONTENT_TYPE / CONTENT_LENGTH`

### 5.4 Response Encoder

职责：

- 将 WSGI 返回结果转换为统一响应对象；
- 编码响应头、响应体和状态码；
- 保留 `id` 等请求关联字段；
- 区分协议层错误与 Django 正常返回的 HTTP 响应。

## 6. 关于 Twisted 的选择

当前结论是：优先选择 **Twisted 作为运行时**，而不是从零开始自定义网络框架。

原因是：

- 目标服务模型接近 `daphne`；
- 项目的真正难点在协议适配和 WSGI 桥接，而不是底层 socket 管理；
- Twisted 在监听、生命周期和协议驱动上更成熟。

但 Twisted 主要负责 runtime / binding 层，协议语义和上层抽象仍然由项目自己定义。

## 7. 当前非目标

第一阶段明确不做的内容包括：

- ASGI 支持；
- 完整标准 gRPC 兼容；
- 按业务接口拆分 protobuf service；
- 双向流；
- 以官方 gRPC server 抽象作为核心执行模型。

## 8. 待继续明确的问题

后续还需要继续收敛的点包括：

1. `RpcRequest` / `RpcResponse` 的具体 protobuf schema；
2. 传输层是否从一开始就严格基于 HTTP/2；
3. `context` 到 WSGI environ / headers 的映射规则；
4. 协议层错误与 Django HTTP 响应的分层表示；
5. `body` 是否在协议上严格定义为 raw bytes，以及如何兼顾 SDK 层的 JSON 友好性。

## 9. 当前工作定义

在当前阶段，可以把 `servicorn` 描述为：

> 一个由 Twisted 驱动的 RPC 网关服务，接收基于 protobuf、风格接近 gRPC 的请求，将其转换为 WSGI 请求后交给 Django 处理，并以接近 daphne 的服务运行方式对外提供能力。

本文档仅记录当前设计方向，后续随着协议和运行时细节明确，需要继续修订。
