#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# ABI Smart Assistant – Quick Demo Launcher
#
# Starts the full stack: Qdrant + Redis + API + SvelteKit Frontend
# Usage: ./run_demo.sh [--down | --logs | --rebuild | --status]
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

# ─── Argument handling ───────────────────────────────────────────

ACTION="start"
REBUILD=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --down)    ACTION="down";    shift ;;
        --logs)    ACTION="logs";    shift ;;
        --rebuild) REBUILD="--build"; shift ;;
        --status)  ACTION="status";  shift ;;
        --help|-h)
            echo "Usage: ./run_demo.sh [--down | --logs | --rebuild | --status | --help]"
            exit 0 ;;
        *)
            echo "[ERROR] Unknown option: $1"
            echo "Usage: ./run_demo.sh [--down | --logs | --rebuild | --status | --help]"
            exit 1 ;;
    esac
done

# ─── Quick commands ──────────────────────────────────────────────

if [ "$ACTION" = "down" ]; then
    echo "Stopping all services…"
    docker compose down
    echo "Done."
    exit 0
fi

if [ "$ACTION" = "logs" ]; then
    docker compose logs -f --tail=100
    exit 0
fi

if [ "$ACTION" = "status" ]; then
    docker compose ps
    exit 0
fi

# ─── Pre-flight checks ──────────────────────────────────────────

echo "ABI Smart Assistant – Demo Launcher"
echo "===================================="
echo ""

# 1. Check for .env
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "[!] .env not found. Copying from .env.example…"
        cp .env.example .env
        echo ""
        echo "    Edit .env and set your API key, then run again:"
        echo "    OPENAI_API_KEY=sk-... | GOOGLE_API_KEY=AIza... | AZURE_OPENAI_API_KEY=..."
        exit 1
    else
        echo "[ERROR] .env and .env.example not found."
        exit 1
    fi
fi

# 2. Validate that at least one API key is configured
set -a
source .env 2>/dev/null || true
set +a

if [ -z "${OPENAI_API_KEY:-}" ] && [ -z "${GOOGLE_API_KEY:-}" ] && [ -z "${AZURE_OPENAI_API_KEY:-}" ]; then
    echo "[ERROR] No API key in .env. Set OPENAI_API_KEY, GOOGLE_API_KEY, or AZURE_OPENAI_API_KEY."
    exit 1
fi

# 3. Check Docker
if ! command -v docker &>/dev/null; then
    echo "[ERROR] Docker not found. Install Docker Desktop first."
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    echo "[ERROR] Docker daemon not running. Start Docker Desktop first."
    exit 1
fi

# ─── Start services ─────────────────────────────────────────────

echo "[1/5] Building containers…"
if [ -n "$REBUILD" ]; then
    docker compose build
else
    docker compose build --quiet
fi

echo "[2/5] Starting Qdrant + Redis…"
docker compose up -d qdrant redis

for i in $(seq 1 30); do
    if curl -sf http://localhost:6333/healthz >/dev/null 2>&1; then break; fi
    if [ "$i" -eq 30 ]; then
        echo "[ERROR] Qdrant not healthy after 30s. Run: docker compose logs qdrant"
        exit 1
    fi
    sleep 1
done
echo "      Qdrant ready."

for i in $(seq 1 15); do
    if docker exec abi-redis redis-cli ping 2>/dev/null | grep -q PONG; then
        echo "      Redis ready."
        break
    fi
    if [ "$i" -eq 15 ]; then echo "[!] Redis not responding (continuing without cache)."; fi
    sleep 1
done

echo "[3/5] Starting API…"
docker compose up -d app

API_OK=false
for i in $(seq 1 20); do
    if curl -sf http://localhost:8000/api/v1/health >/dev/null 2>&1; then
        API_OK=true
        break
    fi
    sleep 1
done
if [ "$API_OK" = true ]; then
    echo "      API ready."
else
    echo "[!] API not responding yet. Run: docker compose logs app"
fi

echo "[4/5] Starting frontend…"
docker compose up -d frontend

echo "[5/5] Ingesting documents…"
docker exec abi-assistant python main.py --ingest-only 2>/dev/null \
    || echo "      (documents may already be ingested)"

echo ""
echo "All services running:"
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Qdrant:    http://localhost:6333/dashboard"
echo ""
echo "Quick commands:"
echo "  ./run_demo.sh --down     Stop everything"
echo "  ./run_demo.sh --logs     Tail all logs"
echo "  ./run_demo.sh --status   Show container status"
echo ""
