#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────────
# MCP Fabric — Docker Install & Start Script
# ──────────────────────────────────────────────────────────────────
# This script checks for Docker prerequisites, installs anything
# missing (on macOS with Homebrew or Linux with apt), builds the
# images, and starts the full stack.
#
# Usage:
#   ./scripts/docker-setup.sh            # Check + build + start
#   ./scripts/docker-setup.sh --build    # Force rebuild
#   ./scripts/docker-setup.sh --up       # Start existing containers
#   ./scripts/docker-setup.sh --down     # Stop everything
# ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── Parse flags ─────────────────────────────────────────────
ACTION="up"
if [[ $# -gt 0 ]]; then
  case "$1" in
    --build) ACTION="build" ;;
    --up)    ACTION="up" ;;
    --down)  ACTION="down" ;;
    *)       error "Unknown flag: $1. Use --build, --up, or --down." ;;
  esac
fi

echo "┌──────────────────────────────────────────────┐"
echo "│        MCP Fabric — Docker Setup             │"
echo "└──────────────────────────────────────────────┘"
echo ""

# ── Check Docker ────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  error "Docker not found.

Install Docker Desktop:
  macOS: https://docs.docker.com/desktop/install/mac-install/
  Linux: curl -fsSL https://get.docker.com | sh
  Or use your package manager."
fi
info "Docker $(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1) found"

# ── Check Docker is running ─────────────────────────────
if ! docker info &>/dev/null; then
  warn "Docker daemon not running. Attempting to start..."

  if [[ "$(uname)" == "Darwin" ]]; then
    open -a Docker && sleep 15
  elif command -v systemctl &>/dev/null; then
    sudo systemctl start docker && sleep 3
  fi

  if ! docker info &>/dev/null; then
    error "Could not start Docker. Please start Docker Desktop manually."
  fi
fi
info "Docker daemon is running"

# ── Check Docker Compose ────────────────────────────────
if docker compose version &>/dev/null; then
  COMPOSE="docker compose"
  info "Docker Compose v$(docker compose version --short) found"
elif command -v docker-compose &>/dev/null; then
  COMPOSE="docker-compose"
  info "docker-compose v$(docker-compose version --short) found"
else
  error "Docker Compose not found.

  macOS: Included with Docker Desktop.
  Linux: sudo apt install docker-compose-plugin"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# ── Actions ─────────────────────────────────────────────
case "$ACTION" in
  build)
    echo ""
    info "Building Docker images..."
    $COMPOSE build
    info "Build complete. Run './scripts/docker-setup.sh --up' to start."
    ;;
  up)
    echo ""
    info "Starting full stack..."
    $COMPOSE up -d
    echo ""
    info "Services:"
    echo "  API:     http://localhost:8000"
    echo "  Docs:    http://localhost:8000/docs"
    echo "  Health:  http://localhost:8000/health"
    echo "  UI:      http://localhost:3000"
    echo ""
    info "Run '$COMPOSE logs -f' to follow logs."
    ;;
  down)
    echo ""
    info "Stopping all services..."
    $COMPOSE down
    info "Done."
    ;;
esac
