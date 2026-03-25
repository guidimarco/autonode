#!/usr/bin/env bash
# Quick sanity check for local MCP development (venv, .env, Inspector command).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "ERROR: .venv not found at ${ROOT}/.venv"
  echo "  Create it: python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'"
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "WARN: .env missing. Copy .env.example to .env and set OPEN_ROUTER_API_KEY."
else
  if ! grep -qE '^[[:space:]]*OPEN_ROUTER_API_KEY=[^[:space:]]' .env; then
    echo "WARN: OPEN_ROUTER_API_KEY appears missing or empty in .env"
  else
    echo "OK: OPEN_ROUTER_API_KEY is set in .env"
  fi
fi

echo ""
echo "Inspector command (run from repo root, paths absolute):"
echo "  DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector \"${ROOT}/.venv/bin/python\" \"${ROOT}/src/autonode/presentation/mcp/server.py\""
