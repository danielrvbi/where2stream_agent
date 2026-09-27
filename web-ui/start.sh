#!/usr/bin/env bash
set -euo pipefail

WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$WEB_DIR/.." && pwd)"
export PYTHONPATH="$PROJECT_DIR/python${PYTHONPATH:+:$PYTHONPATH}"

cd "$WEB_DIR"
if [[ ! -d node_modules ]]; then
    npm ci
fi

python3 -m uvicorn movie_agent.api:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT

npm run dev
