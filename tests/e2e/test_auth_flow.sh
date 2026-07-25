#!/usr/bin/env bash
# test_auth_flow.sh — Tests authentication and admin bootstrap lifecycle.
#
# Endpoints tested:
#   POST /v1/auth/connect — creates an agent token without prior auth
#   POST /v1/auth/setup   — bootstraps the first admin user (201)
#   POST /v1/auth/login   — authenticates with password (200, returns token)
#
# Expected sequence:
#   1. Unauthenticated connect → 200 (agent token issued)
#   2. First-time admin setup  → 201 (bootstrap)
#   3. Login with credentials  → 200 (returns bearer token)

set -euo pipefail

API_URL="${1:-http://localhost:8000}"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { printf "${GREEN}[PASS]${NC} %s\n" "$*"; }
fail() { printf "${RED}[FAIL]${NC} %s\n" "$*"; exit 1; }

# 1. Connect without token — expect 200 and a token
echo "--- POST /v1/auth/connect (no token) ---"
resp=$(curl -sf -X POST "$API_URL/v1/auth/connect" \
    -H "Content-Type: application/json" \
    -d '{"username":"test-agent","password":"ignored"}' 2>&1) || fail "connect request failed"
connect_token=$(printf "%s" "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)
if [ -z "$connect_token" ]; then
    fail "connect response did not include a token. Response: $resp"
fi
pass "connect without token returned 200 with token"

# 2. Bootstrap first admin — expect 201
echo "--- POST /v1/auth/setup ---"
resp=$(curl -sf -X POST "$API_URL/v1/auth/setup" \
    -H "Content-Type: application/json" \
    -d '{"password":"Admin123!"}' 2>&1) || fail "setup request failed"
token=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)
if [ -z "$token" ]; then
    fail "setup response did not include a token. Response: $resp"
fi
pass "admin setup returned 201 with token"

# 3. Login with credentials — expect 200
echo "--- POST /v1/auth/login ---"
resp=$(curl -sf -X POST "$API_URL/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"Admin123!"}' 2>&1) || fail "login request failed"
login_token=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)
if [ -z "$login_token" ]; then
    fail "login response did not include a token. Response: $resp"
fi
pass "login returned 200 with token"
