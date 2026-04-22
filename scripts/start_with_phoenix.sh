#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv. Create it first with: python3 -m venv .venv"
  exit 1
fi

source .venv/bin/activate

if ! command -v phoenix >/dev/null 2>&1; then
  echo "Missing Phoenix CLI."
  echo "Install it in the virtualenv with: pip install arize-phoenix"
  exit 1
fi

export PHOENIX_ENABLE_TRACING=true
export PHOENIX_PROJECT_NAME="${PHOENIX_PROJECT_NAME:-chemistry-course-ai-tutor}"
export PHOENIX_COLLECTOR_ENDPOINT="${PHOENIX_COLLECTOR_ENDPOINT:-http://127.0.0.1:6006/v1/traces}"
export PHOENIX_WORKING_DIR="${PHOENIX_WORKING_DIR:-${ROOT_DIR}/.phoenix_runtime}"

mkdir -p "$PHOENIX_WORKING_DIR"

PHOENIX_LOG="${ROOT_DIR}/.phoenix.log"
APP_LOG="${ROOT_DIR}/.ai-tutor.log"

cleanup() {
  local exit_code=$?
  if [[ -n "${APP_PID:-}" ]]; then
    kill "$APP_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${PHOENIX_PID:-}" ]]; then
    kill "$PHOENIX_PID" >/dev/null 2>&1 || true
  fi
  wait >/dev/null 2>&1 || true
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

echo "Starting Phoenix on http://127.0.0.1:6006"
phoenix serve >"$PHOENIX_LOG" 2>&1 &
PHOENIX_PID=$!

sleep 3

echo "Starting AI tutor UI on http://127.0.0.1:8000"
uvicorn app.main:app >"$APP_LOG" 2>&1 &
APP_PID=$!

echo "Phoenix logs: $PHOENIX_LOG"
echo "AI tutor logs: $APP_LOG"
echo "Press Ctrl+C to stop both services."

wait "$APP_PID"
