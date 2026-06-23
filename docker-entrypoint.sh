#!/usr/bin/env bash
set -Eeuo pipefail

uvicorn server.main:app --host 127.0.0.1 --port 8000 --workers 1 &
api_pid=$!

nginx -g "daemon off;" &
nginx_pid=$!

shutdown() {
  kill -TERM "${api_pid}" "${nginx_pid}" 2>/dev/null || true
  wait "${api_pid}" "${nginx_pid}" 2>/dev/null || true
}

trap shutdown INT TERM EXIT

wait -n "${api_pid}" "${nginx_pid}"
exit_code=$?
shutdown
exit "${exit_code}"
