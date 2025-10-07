#!/usr/bin/env bash
set -euo pipefail
# cd to repo root; fall back to script-relative root
if ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$ROOT"
else
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  cd "$ROOT"
fi

# Development: prefer local source via uv run (fast with cache) or system Python fallback
if [ -d "$ROOT/src/directive" ]; then
  export PYTHONUNBUFFERED=1
  export PYTHONPATH="${ROOT}/src${PYTHONPATH+:$PYTHONPATH}"
  if command -v uv >/dev/null 2>&1; then
    exec uv run python -u -m directive.cli mcp serve
  else
    exec python3 -u -m directive.cli mcp serve
  fi
fi

# Installed: console script on PATH
if command -v directive >/dev/null 2>&1; then
  exec directive mcp serve
fi

echo "directive launcher not found. Install with: pipx install directive, or develop locally with src/ present." >&2
exit 127
