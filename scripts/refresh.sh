#!/usr/bin/env bash
# refresh.sh — update both memories in one command
#
# Usage:
#   ./scripts/refresh.sh              # update graph + RAG index
#   ./scripts/refresh.sh --graph-only # graph only (no DB needed)
#   ./scripts/refresh.sh --rag-only   # RAG index only
#
# Run this whenever you:
#   - add/change a file in docs/personal/  (triggers both)
#   - add/change source code               (graph auto-detects code-only, free)
#   - finish a day's work and want context fresh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_ROOT/.venv/bin/python3"

GRAPH=true
RAG=true

for arg in "$@"; do
  case $arg in
    --graph-only) RAG=false ;;
    --rag-only)   GRAPH=false ;;
  esac
done

echo "=== refresh: updating project memories ==="

# ── 1. Graphify knowledge graph ─────────────────────────────────────────────
if [ "$GRAPH" = true ]; then
  echo ""
  echo "→ graphify: incremental graph update..."
  if [ ! -f "$PROJECT_ROOT/graphify-out/graph.json" ]; then
    echo "  No existing graph found — running full build (first time)."
    cd "$PROJECT_ROOT" && "$PYTHON" -m graphify . --no-viz 2>&1 | tail -5
  else
    cd "$PROJECT_ROOT" && "$PYTHON" -m graphify . --update --no-viz 2>&1 | tail -5
  fi
  echo "  ✓ graph.json updated"
fi

# ── 2. pgvector RAG index ────────────────────────────────────────────────────
if [ "$RAG" = true ]; then
  echo ""
  echo "→ RAG: re-indexing docs/personal/ into pgvector..."
  if [ ! -f "$SCRIPT_DIR/index_context.py" ]; then
    echo "  ⚠ scripts/index_context.py not built yet (Day 4 task — skip for now)"
  else
    cd "$PROJECT_ROOT" && "$PYTHON" "$SCRIPT_DIR/index_context.py" 2>&1 | tail -5
    echo "  ✓ pgvector context chunks updated"
  fi
fi

echo ""
echo "=== done ==="
