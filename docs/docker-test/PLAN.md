# MCP Fabric — Docker Test Plan

> **Version:** 1.0  
> **Status:** Approved  
> **Last updated:** 2026-07-24  

---

## 1. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker Host                                  │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────────┐ │
│  │          │  │          │  │          │  │                     │ │
│  │  API     │  │  UI      │  │  Worker  │  │  Beat               │ │
│  │  :8000   │  │  :3000   │  │  Celery  │  │  Celery Scheduler   │ │
│  │          │  │          │  │          │  │                     │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────────────────────┘ │
│       │             │             │                                 │
│       └─────────────┼─────────────┘                                 │
│                     │                                               │
│  ┌──────────────────┴──────────────────────────────────────────┐   │
│  │                     Service Layer                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │   │
│  │  │PostgreSQL│  │  Redis   │  │   OPA    │                    │   │
│  │  │  :5432   │  │  :6379   │  │  :8181   │                    │   │
│  │  └──────────┘  └──────────┘  └──────────┘                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Test Services                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │   │
│  │  │  test-   │  │  test-   │  │  test-   │  │  test-e2e-  │  │   │
│  │  │  backend │  │  ui      │  │  e2e     │  │  curl       │  │   │
│  │  │  (pytest)│  │  (vitest)│  │(Playwright│  │  (shell)    │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Container Roles

| Container | Image | Purpose | Depends On |
|---|---|---|---|
| `api` | `mcp-fabric-api` (local build) | FastAPI server | postgres, redis, opa |
| `ui` | `mcp-fabric-ui` (local build) | React admin UI | api |
| `worker` | `mcp-fabric-api` | Celery async tasks | postgres, redis |
| `beat` | `mcp-fabric-api` | Celery scheduled tasks | postgres, redis |
| `postgres` | `postgres:16-alpine` | Primary database | — |
| `redis` | `redis:7-alpine` | Cache, broker, rate-limit | — |
| `opa` | `openpolicyagent/opa:latest` | Policy evaluation engine | — |

### Test Containers (docker-compose.test.yml)

| Container | Image | Tests | Reports To |
|---|---|---|---|
| `test-backend` | `mcp-fabric-api` | pytest (unit + integration) | `test-results/` volume |
| `test-ui` | `mcp-fabric-ui` | vitest (128 tests) | `test-results/` volume |
| `test-e2e` | `playwright:v1.52.0` | Playwright (21 tests + screenshots) | `test-results/` volume |
| `test-e2e-curl` | `mcp-fabric-api` | curl E2E smoke tests | `test-results/` volume |

---

## 2. Test Strategy

### Layers

| Layer | Tool | Location | Infrastructure |
|---|---|---|---|
| Unit (services) | pytest + SQLAlchemy | Laptop or Docker | None (SQLite in-memory) |
| Integration (routes) | pytest + TestClient | Laptop or Docker | Docker (PG, Redis, OPA) |
| API (curl E2E) | bash + curl | Docker only | Full stack |
| UI (components) | Vitest + jsdom | Laptop or Docker | None |
| UI (E2E) | Playwright + Chromium | Docker only | Full stack + UI |
| Policy | `opa test` | Laptop or CI | OPA CLI |

### Execution Order

```
1. docker compose up -d postgres redis opa    # Start dependencies
2. docker compose up -d api                    # Start API
3. make test-quick                             # Backend unit (no Docker needed)
4. make test-ui                                # UI vitest (no Docker needed)
5. make test-integration-local                 # Backend integration (needs Docker PG)
6. docker compose -f docker-compose.test.yml up  # Full stack in Docker
7. make test-ui-e2e                            # Playwright (needs Docker + UI)
```

### Pass Criteria

- All backends: 0 failures, 0 errors
- UI vitest: 128/128 passing
- UI Playwright: 21/21 passing, all 19 screenshots captured
- API E2E curl: 5/5 scripts passing (health, auth, registration, capabilities, walkthrough)
- OPA policy: 12/12 tests passing

---

## 3. Test Commands

### From Laptop (using Docker services)

```bash
# Start infrastructure (PostgreSQL, Redis, OPA)
docker compose up -d postgres redis opa

# Run API migrations
poetry run alembic upgrade head

# Start the API
docker compose up -d api

# Run backend unit tests (SQLite, no Docker needed)
make test-quick

# Run backend integration tests (against Docker PostgreSQL)
DATABASE_URL=postgresql+asyncpg://fabric:fabric@localhost:5432/mcp_fabric \
  poetry run pytest tests/routers/ -v

# Run UI vitest (no Docker needed)
make test-ui

# Run UI Playwright E2E (needs UI built and running)
make test-ui-e2e
```

### Inside Docker (everything containerized)

```bash
# Start full stack
docker compose up -d

# Run all tests inside Docker
docker compose -f docker-compose.test.yml up \
  test-backend test-ui test-e2e test-e2e-curl

# Collect results
docker run --rm -v test-results:/results alpine ls -la /results
```

### CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml runs:
# 1. lint + typecheck (no Docker)
# 2. test-sqlite (unit tests, no Docker)
# 3. test-postgres (integration, needs PG service)
# 4. opa-tests (no Docker)
# 5. ui-lint + ui-test (no Docker)
# 6. ui-e2e (needs build + preview)
```

---

## 4. Test Results

Results are captured to `docs/docker-test/results/` after each run:

| Run | Date | Backend | UI Vitest | Playwright | API E2E | OPA |
|---|---|---|---|---|---|---|
| | | | | | | |

### Screenshots

Playwright E2E captures 19 screenshots of all admin UI pages:

| # | Screenshot | Page |
|---|---|---|
| 1 | `01-login.png` | Login form |
| 2 | `02-dashboard.png` | Dashboard with stat cards |
| 3 | `03-servers.png` | Server registry table |
| 4 | `04-servers-register-modal.png` | Register server modal |
| 5 | `05-capabilities.png` | Capability catalog |
| 6 | `06-capabilities-create-modal.png` | Create capability modal |
| 7 | `07-agent-classes.png` | Agent classes table |
| 8 | `08-policies.png` | Policy editor |
| 9 | `09-policies-editor.png` | Rego editor modal |
| 10 | `10-audit.png` | Audit log |
| 11 | `11-approvals.png` | Approvals queue |
| 12 | `12-approvals-review.png` | Review panel |
| 13 | `13-packs.png` | Capability packs |
| 14 | `14-alerts.png` | Alerts |
| 15 | `15-admin-users.png` | Admin user management |
| 16 | `16-admin-users-invite.png` | Invite user modal |
| 17 | `17-trust-posture.png` | Trust posture view |
| 18 | `18-trust-posture-class-selected.png` | Trust with class selected |
| 19 | `19-servers-filtered.png` | Filtered server list |

---

## 5. Test Data

### Mock Servers (used by Playwright API interceptors)

| Server | Endpoint | Tools | Trust Level |
|---|---|---|---|
| KB Server | `http://kb.internal:3001` | search_kb, get_article | trusted |
| Code Search | `http://codesearch.internal:3002` | search_code, search_symbols | trusted |
| Vuln Scanner | `http://security.internal:3003` | scan, list_dependencies | restricted |
| Deployment | `http://deploy.internal:3004` | deploy, rollback, health_check | approval-gated |
| New Unreviewed | `http://new.internal:3005` | (varies) | unreviewed |
| Git History | `http://git.internal:3006` | git_diff, git_log, git_status | trusted |

### Test Users

| Username | Role | MFA |
|---|---|---|
| priya | admin | Enabled |
| jordan | admin | Enabled |
| alex | editor | Disabled |

---

## 6. Output Artifacts

| Artifact | Location | Format |
|---|---|---|
| Test run report | `docs/docker-test/results/YYYY-MM-DD-run-N.md` | Markdown |
| JUnit XML | `test-results/` (Docker volume) | XML |
| Playwright screenshots | `docs/ui-test/findings/screenshots/` | PNG |
| Playwright HTML report | `docs/ui-test/findings/playwright-report/` | HTML |
| Coverage report | `coverage/` (local), `coverage.xml` (CI) | HTML/XML |
