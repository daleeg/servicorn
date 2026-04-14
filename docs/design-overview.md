sh# Servicorn Design Overview

## 1. Project Goal

`servicorn` aims to launch Django applications with a service model similar to `daphne`, while prioritizing support for a gRPC-style RPC protocol.

The first stage does **not** target ASGI. The primary execution target is existing Django applications exposed through **WSGI**.

The core idea is:

- clients invoke a structured RPC API;
- the server receives a normalized RPC request;
- the request is converted into a WSGI request;
- Django handles the request using its existing routing, middleware, and view stack;
- the response is converted back into an RPC response.

## 2. Current Positioning

This project is **not** a standard gRPC service implementation.

The current direction is:

- service runtime modeled after `daphne`;
- transport semantics inspired by gRPC/HTTP2;
- request model close to HTTP/1 request semantics;
- Django integration through WSGI;
- protobuf used as the preferred native message definition format.

In short, this is closer to an **RPC-to-WSGI Django gateway server** than a conventional gRPC application server.

## 3. Protocol Direction

### 3.1 External Client API

The client-facing API can remain structured and friendly, using a JSON-RPC-like shape:

- `jsonrpc`
- `id`
- `method`
- `params.request`
- `params.context`

At this layer:

- `query` may be structured;
- `body` may be structured;
- the SDK is responsible for normalization and encoding.

### 3.2 Internal Transport Request

Before transmission, the client request should be normalized into an HTTP-like request model:

- `http_method`
- `path`
- `query_string`
- `headers`
- `body`
- `context`

Design rules currently agreed:

- `headers` should preserve HTTP semantics and repeated values;
- `query` should be normalized into `query_string`;
- `body` should be encoded before transport;
- the server should receive a normalized request, not a mixed structured/raw request.

## 4. Message Encoding

The preferred direction is to use **protobuf messages**, but not necessarily standard gRPC service definitions.

That means:

- use protobuf for stable request/response schemas;
- do not bind the first version to standard gRPC `service` / `rpc` definitions;
- use protobuf `message` as the transport contract;
- keep the server-side protocol under project control.

This allows:

- strong schema constraints;
- future multi-language client support;
- binary-safe payload handling;
- reduced server-side reprocessing before WSGI conversion.

## 5. Server Architecture

The current server is split into four core modules.

### 5.1 Runtime

Suggested implementation basis: **Twisted**.

Responsibilities:

- listening and binding;
- connection lifecycle;
- timeout handling;
- TLS and future socket/fd support;
- graceful shutdown;
- base logging and runtime control.

This layer should not understand Django business logic.

### 5.2 RPC Protocol

Responsibilities:

- receive and parse incoming RPC messages;
- validate the envelope and request structure;
- decode protobuf payloads or equivalent transport messages;
- output a normalized internal request object.

This layer should not construct WSGI directly.

### 5.3 WSGI Bridge

This is the core module.

Responsibilities:

- convert normalized RPC requests into WSGI `environ`;
- map request metadata into headers or custom environ fields;
- load and invoke the Django WSGI application;
- collect status, headers, and body from the application response.

Typical mapping includes:

- `http_method -> REQUEST_METHOD`
- `path -> PATH_INFO`
- `query_string -> QUERY_STRING`
- `body -> wsgi.input`
- `headers -> HTTP_* / CONTENT_TYPE / CONTENT_LENGTH`

### 5.4 Response Encoder

Responsibilities:

- convert the WSGI result into a normalized response object;
- encode headers, body, and status;
- preserve request correlation fields such as `id`;
- distinguish protocol-layer errors from Django-generated HTTP responses.

## 6. Twisted Decision

Current conclusion: prefer **Twisted as the runtime**, rather than building a custom network framework from scratch.

Reasoning:

- the desired service model is close to `daphne`;
- the difficult part of this project is protocol adaptation and WSGI bridging, not raw socket management;
- Twisted provides a mature runtime model for listeners, lifecycle, and protocol driving.

However, Twisted should mainly own the runtime/binding layer. Upper protocol semantics should remain project-defined.

## 7. Current Non-Goals

The following are explicitly out of scope for the first stage:

- ASGI support;
- full standard gRPC compatibility;
- protobuf service-per-business-interface design;
- bidirectional streaming;
- direct dependence on official gRPC server abstractions as the core execution model.

## 8. Open Questions

These items remain to be refined later:

1. the exact protobuf schema for `RpcRequest` and `RpcResponse`;
2. whether transport is strictly HTTP/2-backed from day one;
3. how request context maps into WSGI environ or headers;
4. how protocol-layer errors are represented separately from Django HTTP responses;
5. whether body is specified as raw bytes only, or also documented with JSON examples for SDK ergonomics.

## 9. Working Definition

At the current stage, `servicorn` can be described as:

> A Twisted-driven RPC gateway that accepts protobuf-based, gRPC-style requests, converts them into WSGI requests, and runs existing Django applications behind a daphne-like service runtime.

This document records the current design direction and should be revised as the protocol and runtime details are clarified.
