#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="/opt/worker/qzh-dlp/servicorn"
PYTHON_BIN="${PYTHON_BIN:-/opt/venv/servicorn/bin/python}"
BACKEND_ROOT="${BACKEND_ROOT:-/opt/worker/qzh-dlp/qzh/legacy/datacenter/backend}"
WSGI_APP="${WSGI_APP:-lucifer.wsgi:application}"
ETCD_BIN="${ETCD_BIN:-etcd}"
ETCD_CLIENT_URL="${ETCD_CLIENT_URL:-http://127.0.0.1:2379}"
ETCD_PEER_URL="${ETCD_PEER_URL:-http://127.0.0.1:2380}"
ETCD_DATA_DIR="${ETCD_DATA_DIR:-/tmp/servicorn-etcd}"
SERVER_HOST="${SERVER_HOST:-127.0.0.1}"
SERVER_PORT="${SERVER_PORT:-50071}"
CLIENT_HOST="${CLIENT_HOST:-127.0.0.1}"
CLIENT_PORT="${CLIENT_PORT:-8015}"
SERVICE_NAME="${SERVICE_NAME:-legacy-lucifer}"
GATEWAY_RPC_PATH="${GATEWAY_RPC_PATH:-/api/v1/gateway_rpc}"
PID_DIR="${PID_DIR:-/tmp/servicorn-legacy}"
RESET_ETCD_DATA="${RESET_ETCD_DATA:-true}"

ETCD_PID_FILE="${PID_DIR}/etcd.pid"
SERVER_PID_FILE="${PID_DIR}/run_server.pid"
CLIENT_PID_FILE="${PID_DIR}/run_client.pid"
ETCD_LOG_FILE="${PID_DIR}/etcd.log"
SERVER_LOG_FILE="${PID_DIR}/run_server.log"
CLIENT_LOG_FILE="${PID_DIR}/run_client.log"

wait_for_http() {
    local url="$1"
    local name="$2"
    local attempts="${3:-30}"

    for _ in $(seq 1 "$attempts"); do
        if curl --noproxy '*' -sS "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done

    echo "$name did not become ready: $url" >&2
    return 1
}

wait_for_tcp() {
    local host="$1"
    local port="$2"
    local name="$3"
    local attempts="${4:-30}"

    for _ in $(seq 1 "$attempts"); do
        if nc -z "$host" "$port" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done

    echo "$name did not become ready: $host:$port" >&2
    return 1
}

ensure_pid_dir() {
    mkdir -p "$PID_DIR"
}

is_running() {
    local pid_file="$1"
    [[ -f "$pid_file" ]] || return 1
    local pid
    pid="$(cat "$pid_file")"
    [[ -n "$pid" ]] || return 1
    kill -0 "$pid" 2>/dev/null
}

stop_process() {
    local name="$1"
    local pid_file="$2"
    if ! [[ -f "$pid_file" ]]; then
        return 0
    fi
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        echo "Stopping $name ($pid)"
        kill "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
}

start_etcd() {
    if is_running "$ETCD_PID_FILE"; then
        echo "etcd is already running"
        return 0
    fi
    if [[ "$RESET_ETCD_DATA" == "true" ]]; then
        mkdir -p "$ETCD_DATA_DIR"
        rm -rf "${ETCD_DATA_DIR}"/*
    fi
    echo "Starting etcd on ${ETCD_CLIENT_URL}"
    nohup "$ETCD_BIN" \
        --listen-client-urls "$ETCD_CLIENT_URL" \
        --advertise-client-urls "$ETCD_CLIENT_URL" \
        --listen-peer-urls "$ETCD_PEER_URL" \
        --data-dir "$ETCD_DATA_DIR" \
        >"$ETCD_LOG_FILE" 2>&1 &
    echo "$!" >"$ETCD_PID_FILE"
    wait_for_http "${ETCD_CLIENT_URL}/health" "etcd"
}

start_server() {
    if is_running "$SERVER_PID_FILE"; then
        echo "run_server is already running"
        return 0
    fi
    echo "Starting run_server on ${SERVER_HOST}:${SERVER_PORT}"
    nohup env \
        PYTHONPATH="${BACKEND_ROOT}:${ROOT_DIR}" \
        KVSTORAGE_ENABLED=false \
        PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
        "$PYTHON_BIN" "$ROOT_DIR/manage.py" \
        --host "$SERVER_HOST" \
        --port "$SERVER_PORT" \
        --wsgi-app "$WSGI_APP" \
        run_server \
        --service-name "$SERVICE_NAME" \
        --register-service \
        >"$SERVER_LOG_FILE" 2>&1 &
    echo "$!" >"$SERVER_PID_FILE"
    wait_for_tcp "$SERVER_HOST" "$SERVER_PORT" "run_server"
}

start_client() {
    if is_running "$CLIENT_PID_FILE"; then
        echo "run_client is already running"
        return 0
    fi
    echo "Starting run_client on ${CLIENT_HOST}:${CLIENT_PORT}"
    nohup env \
        PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
        "$PYTHON_BIN" "$ROOT_DIR/manage.py" \
        --host "$CLIENT_HOST" \
        --port "$CLIENT_PORT" \
        run_client \
        --service-name "$SERVICE_NAME" \
        >"$CLIENT_LOG_FILE" 2>&1 &
    echo "$!" >"$CLIENT_PID_FILE"
    wait_for_http "http://${CLIENT_HOST}:${CLIENT_PORT}/docs" "run_client"
}

start_all() {
    ensure_pid_dir
    start_etcd
    start_server
    start_client
    echo "Legacy backend gateway is ready"
    echo "client=http://${CLIENT_HOST}:${CLIENT_PORT}${GATEWAY_RPC_PATH}"
}

stop_all() {
    stop_process "run_client" "$CLIENT_PID_FILE"
    stop_process "run_server" "$SERVER_PID_FILE"
    stop_process "etcd" "$ETCD_PID_FILE"
}

ACTION="${1:-}"
TARGET="${2:-all}"

start_target() {
    ensure_pid_dir
    case "$1" in
        etcd)
            start_etcd
            ;;
        server)
            start_etcd
            start_server
            ;;
        client)
            start_etcd
            start_server
            start_client
            ;;
        all)
            start_all
            ;;
        *)
            echo "Unknown service target: $1" >&2
            exit 1
            ;;
    esac
}

stop_target() {
    case "$1" in
        etcd)
            stop_process "etcd" "$ETCD_PID_FILE"
            ;;
        server)
            stop_process "run_server" "$SERVER_PID_FILE"
            ;;
        client)
            stop_process "run_client" "$CLIENT_PID_FILE"
            ;;
        all)
            stop_all
            ;;
        *)
            echo "Unknown service target: $1" >&2
            exit 1
            ;;
    esac
}

case "$ACTION" in
    start)
        start_target "$TARGET"
        ;;
    stop)
        stop_target "$TARGET"
        ;;
    restart)
        stop_target "$TARGET"
        start_target "$TARGET"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart} [etcd|server|client|all]" >&2
        exit 1
        ;;
esac
