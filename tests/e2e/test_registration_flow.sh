#!/usr/bin/env bash
# test_registration_flow.sh — Tests MCP server registration, listing, and inspection.
#
# Endpoints tested:
#   POST /v1/servers          — register a new MCP server (201)
#   GET  /v1/servers          — list all registered servers (200)
#   POST /v1/servers/{id}/inspect — trigger live inspection (200)
#
# Expected sequence:
#   1. Register a test server → 201 with server data + UUID
#   2. List servers → 200 with the new server in the response
#   3. Inspect server → 200 with probe results

set -euo pipefail

API_URL="${1:-http://localhost:8000}"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { printf "${GREEN}[PASS]${NC} %s\n" "$*"; }
fail() { printf "${RED}[FAIL]${NC} %s\n" "$*"; exit 1; }

# 1. Register a server
echo "--- POST /v1/servers ---"
resp=$(curl -sf -X POST "$API_URL/v1/servers" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "E2E Test Server",
        "endpoint": "http://localhost:3099",
        "owner_team": "e2e",
        "labels": ["test", "e2e"]
    }' 2>&1) || fail "server registration request failed"
server_id=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -z "$server_id" ]; then
    fail "server registration did not return an id. Response: $resp"
fi
pass "server registered with id=$server_id"

# 2. List servers — expect the registered server in the result set
echo "--- GET /v1/servers ---"
resp=$(curl -sf "$API_URL/v1/servers" 2>&1) || fail "list servers request failed"
found=$(echo "$resp" | python3 -c "
import sys,json
data = json.load(sys.stdin)
items = data.get('items', data.get('servers', data if isinstance(data, list) else []))
if isinstance(items, dict):
    items = [items]
for s in items:
    if s.get('id') == '$server_id':
        print('found')
        break
" 2>/dev/null)
if [ "$found" != "found" ]; then
    fail "registered server not found in list. Response: $resp"
fi
pass "server found in list response"

# 3. Inspect the server
echo "--- POST /v1/servers/$server_id/inspect ---"
resp=$(curl -sf -X POST "$API_URL/v1/servers/$server_id/inspect" 2>&1) || fail "inspect request failed"
status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('health_status',''))" 2>/dev/null)
if [ -z "$status" ]; then
    fail "inspect did not return health_status. Response: $resp"
fi
pass "server inspect returned health_status=$status"
