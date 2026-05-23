#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# Scholaris — Start Script
# Launches FastAPI backend + Streamlit frontend in parallel
# Usage:  bash run.sh
# ─────────────────────────────────────────────────────────────────

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "╔══════════════════════════════════════════════╗"
echo "║          Scholaris  v2.0  Startup            ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Check .env
if [ ! -f ".env" ]; then
  echo "⚠  .env not found — copying from .env.example"
  cp .env.example .env 2>/dev/null || true
fi

# Install deps if needed
if ! python -c "import fastapi" 2>/dev/null; then
  echo "📦  Installing dependencies…"
  pip install -r requirements.txt -q
fi

echo "🚀  Starting FastAPI backend  → http://localhost:8000"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 2

echo "🎨  Starting Streamlit frontend → http://localhost:8501"
streamlit run frontend/app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --theme.base dark \
  --theme.primaryColor "#7c6ff7" \
  --theme.backgroundColor "#0d0f1a" \
  --theme.secondaryBackgroundColor "#12141f" \
  --theme.textColor "#e8eaf0" &
FRONTEND_PID=$!

echo ""
echo "──────────────────────────────────────────────"
echo "  Backend  : http://localhost:8000"
echo "  API Docs : http://localhost:8000/docs"
echo "  Frontend : http://localhost:8501"
echo "──────────────────────────────────────────────"
echo "  Press Ctrl+C to stop both services"
echo ""

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT INT TERM
wait
