#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

status=0

echo "=== Environment Check ==="

if command -v gmsh >/dev/null 2>&1; then
  GMSH_VERSION=$(gmsh --version 2>&1 | head -1 || echo "unknown")
  echo "✓ gmsh CLI: $GMSH_VERSION"
else
  echo "✗ gmsh CLI not found in PATH"
  status=1
fi

if [ -x ".venv/bin/python" ]; then
  echo "✓ venv: .venv"
else
  echo "✗ venv not found (.venv/bin/python missing)"
  status=1
fi

if [ -x ".venv/bin/python" ]; then
  if .venv/bin/python -c "import numpy" >/dev/null 2>&1; then
    echo "✓ numpy (venv)"
  else
    echo "✗ numpy missing in venv"
    status=1
  fi
fi

if [ $status -ne 0 ]; then
  echo
  echo "Fixes:"
  echo "  1) Create venv:  python3 -m venv .venv"
  echo "  2) Install deps: .venv/bin/pip install -r gmsh-learning/requirements.txt"
  echo "  3) Ensure gmsh CLI is installed and on PATH"
  exit $status
fi

echo "=== OK ==="
