#!/usr/bin/env bash

set -euo pipefail

CLIENT_HOST="${CLIENT_HOST:-127.0.0.1}"
CLIENT_PORT="${CLIENT_PORT:-8015}"
SERVICE_NAME="${SERVICE_NAME:-legacy-lucifer}"
REQUEST_PATH="${REQUEST_PATH:-/api/v1/version/}"
REQUEST_ID="${REQUEST_ID:-req-legacy-version}"
TRACE_ID="${TRACE_ID:-trace-legacy-version}"
COMPANY_ID="${COMPANY_ID:-f7007ddf-efb3-4f54-94a7-b440639a4de7}"
APP_NAME="${APP_NAME:-qzh}"
GATEWAY_RPC_PATH="${GATEWAY_RPC_PATH:-/api/v1/gateway_rpc}"

curl --noproxy '*' -sS -X POST "http://${CLIENT_HOST}:${CLIENT_PORT}${GATEWAY_RPC_PATH}" \
    -H 'Content-Type: application/json' \
    --data "{
  \"jsonrpc\": \"2.0\",
  \"request_id\": \"${REQUEST_ID}\",
  \"method\": \"grpcCall\",
  \"params\": {
    \"http_method\": \"GET\",
    \"path\": \"${REQUEST_PATH}\",
    \"headers\": [
      [\"X-CS-Header-Company\", \"${COMPANY_ID}\"],
      [\"X-CS-Header-App\", \"${APP_NAME}\"]
    ],
    \"body\": null,
    \"context\": {
      \"service_name\": \"${SERVICE_NAME}\",
      \"trace_id\": \"${TRACE_ID}\"
    }
  }
}"
echo
