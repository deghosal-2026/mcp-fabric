# Phase 10: Testing

> **Tasks:** 35 · **Effort:** 40h (5 days, ongoing across weeks 1-4)  
> **Dependencies:** Phases 1-9 (tests written alongside implementation)

## 10.1 Unit Tests — Services (15 tasks)

### T10-01 to T10-15: Unit Tests — Services (#62)
> Registry, Capability, Policy, Routing, Audit, Approval, Pack, Alert, Auth, Tenant, Schema Diff, Errors, Pagination, Batch, Fallback.

Each test: mock dependencies (DB via SQLite, MCP via mock server), assert correct behavior, test edge cases. **Effort:** 15h total.

## 10.2 Integration Tests (8 tasks)

### T10-16: Registration Flow E2E (#65)
**Effort:** 1.5h | **Deps:** Phase 5
POST /servers → verify tools imported → GET /servers/{id} → verify detail → POST inspect → verify diff.
**Success Criteria:** Full flow works with real DB + mock MCP server.

### T10-17: Capability Request E2E (#67)
**Effort:** 1.5h | **Deps:** Phase 5
Register server → create capability → map tool → create class + trust → create token → POST /capability/request → verify response + audit event.
**Success Criteria:** Request routed, response normalized, audit logged.

### T10-18: Approval Flow E2E (#70)
**Effort:** 1.5h | **Deps:** Phase 5
Create approval-gated capability → POST request → verify 202 → create admin → approve → verify routing → verify audit.
**Success Criteria:** Full approval lifecycle with Celery notification.

### T10-19: Fallback Flow E2E (#73)
**Effort:** 1.5h | **Deps:** Phase 5
Mock primary server timeout → POST request → verify fallback server used → verify degradation logged → verify alert created.
**Success Criteria:** Failover transparent to agent. Alert fired.

### T10-20: Batch Flow E2E (#76)
**Effort:** 1h | **Deps:** Phase 5
POST /capability/batch with 3 requests → verify 3 parallel responses → verify mixed success/failure → verify 3 audit events.
**Success Criteria:** Parallel execution. Mixed results correct.

### T10-21: Auth Flow E2E (#79)
**Effort:** 1.5h | **Deps:** Phase 5
Create token → POST /auth/connect → verify capability surface → revoke token → verify 401 → rotate token → verify both work during grace → old invalid after.
**Success Criteria:** Full token lifecycle. Grace period works.

### T10-22: Pack Flow E2E (#307)
**Effort:** 1h | **Deps:** Phase 5
Create pack → add capabilities → assign to class → create agent in class → connect → verify surface includes pack → deprecate capability → verify removed from pack.
**Success Criteria:** Pack-capability-class wiring works. Auto-removal on deprecate.

### T10-23: Migration Flow (v0.1.0 stub) (#308)
**Effort:** 0.5h | **Deps:** None
GET /v1/admin/migration/status → verify returns empty/template response.
**Success Criteria:** Endpoint exists, returns 200 with empty migration data.

## 10.3 OPA Policy Tests (3 tasks)

### T10-24: Default Policy Tests (#309)
**Effort:** 1h | **Deps:** P0-12
Run `opa test policies/ -v` → verify all 10 tests pass → add custom test: cross-team deny, cross-team allow when shared.
**Success Criteria:** 12/12 tests pass. CI opa-tests job green.

### T10-25: Policy Deploy Integration Test (#310)
**Effort:** 1h | **Deps:** P0-12, Phase 5
Deploy updated rego via POST /v1/admin/policies/bundle → verify OPA endpoint reflects new policy → verify Redis OPA cache invalidated → verify next capability request uses new policy.
**Success Criteria:** Deploy → OPA updates. Cache invalidated. Next request respects new policy.

### T10-26: Secure Fail-Closed Test (#311)
**Effort:** 0.5h | **Deps:** Phase 5
Stop OPA → make capability request → verify 503 → verify no request routed (deny by default) → start OPA → verify requests resume.
**Success Criteria:** OPA down = all denied. OPA back = normal operation.

## 10.4 UI Component + Integration Tests (5 tasks)

### T10-27: UI Test Infrastructure (#321)
**Effort:** 2h | **Deps:** Phase 9
Install Vitest, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event, jsdom → configure vitest.config.ts with jsdom environment → set up test setup file (cleanup, matchers) → configure npm test script → verify `npm test` runs a placeholder.
**Success Criteria:** `npm test` runs. Testing library renders a React component. DOM assertions work.

### T10-28: Shared Component Tests (#322)
**Effort:** 3h | **Deps:** T10-27
Tests for: LoadingState (renders correct number of skeleton rows) → ErrorState (message renders, retry button fires callback) → EmptyState (message renders, action button fires) → Badge (correct color class per variant) → Modal (opens/closes, Esc key closes, overlay click closes) → Toast (message appears, auto-dismisses after 5s).
**Success Criteria:** All shared component states tested. 20+ tests. Assertions on render, events, and accessibility.

### T10-29: Page Component Tests (#323)
**Effort:** 3h | **Deps:** T10-27
Wrap pages in test providers (QueryClientProvider, BrowserRouter, ToastProvider) → mock API client functions → test: LoginPage (renders form, submits, shows error, MFA flow) → DashboardPage (renders stat cards with mock data, handles empty state) → ServersPage (renders table, filter changes query, register modal opens/submits).
**Success Criteria:** Login, Dashboard, and Servers page tests pass. Mock API data renders correctly. Loading/error states tested.

### T10-30: Auth Flow Integration Test (#324)
**Effort:** 2h | **Deps:** T10-27
Mock login API → render LoginPage → fill form → submit → verify authStore updated → verify redirect to / → mock 401 response → verify redirect to /login → verify token cleared from localStorage.
**Success Criteria:** Full auth lifecycle tested. Token persistence and clearance verified.

### T10-31: Navigation + Protected Routes Test (#325)
**Effort:** 1h | **Deps:** T10-27
Render App with no token → verify redirect to /login → set token in store → render App → verify sidebar renders role-filtered links → click each nav link → verify correct page route → logout → verify redirect.
**Success Criteria:** Protected route redirects unauthenticated. All 11 nav links navigate correctly. Role filtering works.

## 10.5 E2E Tests (3 tasks)

### T10-32: Docker Compose Smoke Test (#312)
**Effort:** 2h | **Deps:** P0-06, All phases
`docker-compose up` → wait for all healthy → curl /v1/health → register server via API → create capability → map → token → capability request → verify audit → decomission → sunset.
**Success Criteria:** Full lifecycle in Docker Compose. All 7 services healthy.

### T10-33: Admin UI E2E Smoke Test (#313)
**Effort:** 1.5h | **Deps:** Phase 9, T10-27
Login → dashboard loads → navigate servers → register → verify detail → navigate capabilities → create → map → navigate audit → verify events.
**Success Criteria:** All 12 pages render. Navigation works. API calls succeed.

### T10-34: First-Time Deployment Walkthrough (#314)
**Effort:** 1h | **Deps:** All phases
Follow spec Section 14.1 step-by-step (10 curl commands) → verify each step returns expected response → verify entire flow < 10 minutes.
**Success Criteria:** Zero-to-first-request in < 10 min. README commands work exactly.

## 10.6 Test Infrastructure (6 tasks)

### T10-35: Mock MCP Server Fixture (#315)
**Effort:** 2h | **Deps:** P0-13
`tests/fixtures/mock_mcp_server.py` — FastAPI app with /tools/list + /tools/call → configurable tool definitions (code-search: 3 tools, git-history: 2 tools, kb-server: 4 tools, deployment-server: 2 tools) → configurable latency (default 0ms, test modes: 200ms, 2000ms, 6000ms) → configurable failure (timeout, 500 error) → health check endpoint.
**Success Criteria:** Returns tools. Latency/failure injection works. Multiple server instances possible.

### T10-36: Test Database Fixtures (#316)
**Effort:** 1h | **Deps:** P1-51
`tests/conftest.py` — pytest fixtures: test_db (SQLite :memory:), test_settings (testing env), test_client (FastAPI TestClient), auth_headers (agent token), admin_headers (admin token).
**Success Criteria:** Tests use :memory: SQLite, no file I/O. Clean DB per test.

### T10-37: Test Data Factories (#317)
**Effort:** 1.5h | **Deps:** Phase 1
`tests/factories.py` — factory functions: create_test_server(name, tools), create_test_capability(name, domain), create_test_agent_class(name), create_test_token(class), create_test_admin(role). All return ORM objects or response dicts.
**Success Criteria:** One function call creates test data. No manual DB inserts in tests.

### T10-38: Coverage Configuration (#318)
**Effort:** 0.5h | **Deps:** P0-01
pytest-cov config: source=api, omit=tests/*,alembic/*, fail_under=80 → .coveragerc exclusions.
**Success Criteria:** `make test` reports coverage > 80%. Coverage report uploaded to codecov in CI.

### T10-39: Test Markers (#319)
**Effort:** 0.5h | **Deps:** P0-01
Register pytest markers: unit, integration, e2e, slow → tests tagged appropriately → `make test-unit` runs only unit tests → `make test-integration` runs integration → CI test-sqlite runs unit, test-postgres runs integration.
**Success Criteria:** Marker filtering works. Unit tests run < 30s. Integration < 2min.

### T10-40: Test CI Verification (#320)
**Effort:** 0.5h | **Deps:** P0-13, T10-01 through T10-34
Verify CI test-sqlite job passes → verify test-postgres passes → verify coverage uploaded → verify opa-tests passes.
**Success Criteria:** All CI test jobs green. Coverage badge shows >80%.
