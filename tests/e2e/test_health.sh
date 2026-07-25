#!/usr/bin/env bash
# test_health.sh — Verifies the three health-check endpoints.
#
# Endpoints tested:
#   GET /health     — detailed dependency probe; returns {"status":"healthy"}
#   GET /health/ready — Kubernetes readiness probe; returns {"status":"ready"}
#   GET /health/live  — Kubernetes liveness probe; returns {"status":"alive"}
#
# Expected: All three return HTTP 200 with the expected status string.

set -euo pipefail

API_URL="${1:-http://localhost:8000}"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { printf "${GREEN}[PASS]${NC} %s\n" "$*"; }
fail() { printf "${RED}[FAIL]${NC} %s\n" "$*"; exit 1; }

# /health — full dependency check
echo "--- GET /health ---"
resp=$(curl -sf "$API_URL/health" 2>&1) || fail "/health returned non-zero exit"
status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
if [ "$status" != "healthy" ]; then
    fail "/health status is '$status', expected 'healthy'. Response: $resp"
fi
pass "/health returned status=healthy"

# /health/ready — readiness probe
echo "--- GET /health/ready ---"
resp=$(curl -sf "$API_URL/health/ready" 2>&1) || fail "/health/ready returned non-zero exit"
status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
if [ "$status" != "ready" ]; then
    fail "/health/ready status is '$status', expected 'ready'. Response: $resp"
fi
pass "/health/ready returned status=ready"

# /health/live — liveness probe
echo "--- GET /health/live ---"
resp=$(curl -sf "$API_URL/health/live" 2>&1) || fail "/health/live returned non-zero exit"
status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
if [ "$status" != "alive" ]; then
    fail "/health/live status is '$status', expected 'alive'. Response: $resp"
fi
pass "/health/live returned status=alive"
