#!/usr/bin/env bash
# Main E2E test runner for MCP Fabric.
#
# Starts the full Docker Compose stack, waits for all services to become
# healthy, then runs each test script in sequence. Exits with a summary of
# pass/fail counts and tears down the stack on completion.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
E2E_DIR="$(cd "$(dirname "$0")" && pwd)"
PASSED=0
FAILED=0
FAILED_NAMES=()

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { printf "${YELLOW}[INFO]${NC}  %s\n" "$*"; }
pass()  { printf "${GREEN}[PASS]${NC}  %s\n" "$*"; }
fail()  { printf "${RED}[FAIL]${NC}  %s\n" "$*"; }

# --- cleanup handler ---
cleanup() {
    info "Tearing down Docker Compose stack..."
    docker compose -f "$ROOT_DIR/docker-compose.yml" down --volumes --remove-orphans 2>/dev/null || true
}
trap cleanup EXIT

# --- start stack ---
info "Starting Docker Compose stack..."
docker compose -f "$ROOT_DIR/docker-compose.yml" up -d --build

# --- wait for API to be healthy ---
info "Waiting for API to become healthy..."
API_URL="${API_URL:-http://localhost:8000}"
MAX_RETRIES=60
RETRY_INTERVAL=3
RETRIES=0

while true; do
    if curl -sf "$API_URL/health" >/dev/null 2>&1; then
        pass "API is healthy"
        break
    fi
    RETRIES=$((RETRIES + 1))
    if [ "$RETRIES" -ge "$MAX_RETRIES" ]; then
        fail "API did not become healthy within $((MAX_RETRIES * RETRY_INTERVAL)) seconds"
        docker compose -f "$ROOT_DIR/docker-compose.yml" logs api --tail=40
        exit 1
    fi
    sleep "$RETRY_INTERVAL"
done

# --- run test scripts ---
run_test() {
    local script="$1"
    local name
    name="$(basename "$script" .sh)"
    info "Running test: $name"
    if bash "$script" "$API_URL"; then
        pass "$name"
        PASSED=$((PASSED + 1))
    else
        fail "$name"
        FAILED=$((FAILED + 1))
        FAILED_NAMES+=("$name")
    fi
}

TEST_SCRIPTS=(
    "$E2E_DIR/test_health.sh"
    "$E2E_DIR/test_auth_flow.sh"
    "$E2E_DIR/test_registration_flow.sh"
    "$E2E_DIR/test_capability_flow.sh"
    "$E2E_DIR/test_deployment_walkthrough.sh"
)

for script in "${TEST_SCRIPTS[@]}"; do
    run_test "$script"
done

# --- summary ---
echo ""
echo "========================================"
info "Results: ${PASSED} passed, ${FAILED} failed"
if [ "$FAILED" -gt 0 ]; then
    for name in "${FAILED_NAMES[@]}"; do
        fail "  $name"
    done
fi
echo "========================================"

exit "$FAILED"
