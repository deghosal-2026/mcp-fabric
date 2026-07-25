#!/usr/bin/env bash
# test_capability_flow.sh — Tests capability CRUD, mappings, and execution.
#
# Endpoints tested:
#   POST /v1/capabilities                — create a capability (201)
#   POST /v1/capabilities/{id}/mappings  — map to a server tool (201)
#   POST /v1/capability/request          — execute a capability (200)
#
# This script depends on a registered server existing (from
# test_registration_flow.sh). It runs independently by registering a
# throw-away server if none is found.

set -euo pipefail

API_URL="${1:-http://localhost:8000}"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { printf "${GREEN}[PASS]${NC} %s\n" "$*"; }
fail() { printf "${RED}[FAIL]${NC} %s\n" "$*"; exit 1; }

# Helper: register a server and return its id
register_server() {
    curl -sf -X POST "$API_URL/v1/servers" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Cap Flow Test Server",
            "endpoint": "http://localhost:3098",
            "owner_team": "e2e",
            "labels": ["test", "cap-flow"]
        }' 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo ""
}

# 1. Create a capability
echo "--- POST /v1/capabilities ---"
resp=$(curl -sf -X POST "$API_URL/v1/capabilities" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "knowledge:search",
        "domain": "knowledge",
        "description": "Search documentation and knowledge base"
    }' 2>&1) || fail "create capability request failed"
cap_id=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -z "$cap_id" ]; then
    fail "capability creation did not return an id. Response: $resp"
fi
pass "capability created with id=$cap_id"

# 2. Map capability to a server
echo "--- POST /v1/capabilities/$cap_id/mappings ---"
server_id=$(register_server)
if [ -z "$server_id" ]; then
    fail "could not register a server for capability mapping"
fi
resp=$(curl -sf -X POST "$API_URL/v1/capabilities/$cap_id/mappings" \
    -H "Content-Type: application/json" \
    -d "{
        \"server_id\": \"$server_id\",
        \"tool_name\": \"search_kb\",
        \"is_primary\": true
    }" 2>&1) || fail "create capability mapping request failed"
mapping_id=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -z "$mapping_id" ]; then
    fail "mapping creation did not return an id. Response: $resp"
fi
pass "capability mapping created with id=$mapping_id"

# 3. Execute a capability request
echo "--- POST /v1/capability/request ---"
resp=$(curl -sf -X POST "$API_URL/v1/capability/request" \
    -H "Content-Type: application/json" \
    -d '{
        "capability": "knowledge:search",
        "params": {"query": "deployment runbook"}
    }' 2>&1) || fail "capability request failed"
server_name=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('server','<unknown>'))" 2>/dev/null)
latency=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('latency_ms',0))" 2>/dev/null)
pass "capability request routed to server='$server_name' (${latency}ms)"
