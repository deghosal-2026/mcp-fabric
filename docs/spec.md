# MCP Fabric — Technical Specification

> **Status:** Draft v2.0  
> **Last updated:** 2026-07-22  
> **Covers:** PRD v1.0 (29 journeys, 9 features, all scenarios)

---

## 1. Architecture Overview

### 1.1 Codebase Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Admin UI (React + TypeScript)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Dashboard │ │Servers   │ │Policies  │ │Audit Log │ │Approvals │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Catalog   │ │Packs     │ │Alerts    │ │Trust     │ │Users     │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                       │ TanStack Query                               │
│                       │ Zustand (UI state)                           │
└───────────────────────┼──────────────────────────────────────────────┘
                        │ HTTP/2 + JSON       Accept: application/vnd.fabric.v1+json
┌───────────────────────┼──────────────────────────────────────────────┐
│                  Fabric API (FastAPI)                                 │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │                     Middleware Stack                           │   │
│  │  Auth │ Rate Limit │ Tenant Scope │ Audit │ Tracing │ CORS │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐   │
│  │ Registry    │  │ Capability   │  │ Policy       │  │ Routing  │   │
│  │ Routes      │  │ Routes       │  │ Routes       │  │ Routes   │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘   │
│         │                │                │               │          │
│  ┌──────┴────────────────┴────────────────┴───────────────┴──────┐   │
│  │                      Service Layer                            │   │
│  │                                                                │   │
│  │  RegistryService  CapabilityService  PolicyService             │   │
│  │  RoutingService   AuditService       ApprovalService           │   │
│  │  PackService      AlertService       AuthService               │   │
│  │  SandboxService   TenantService                                │   │
│  │                                                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │              MCP Client Layer                            │  │   │
│  │  │  ServerInspector   ToolCaller   SchemaDiffer             │  │   │
│  │  │  (uses official `mcp` Python SDK)                        │  │   │
│  │  └──────────────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Data Access Layer                           │    │
│  │                                                                │    │
│  │  SQLAlchemy 2.0 (async)                                       │    │
│  │  ├── SQLite engine (local dev, single-user)                    │    │
│  │  └── PostgreSQL engine (production, team use)                  │    │
│  │                                                                │    │
│  │  Redis (async)                                                 │    │
│  │  ├── Agent sessions (TTL-based)                                │    │
│  │  ├── Rate limit counters (atomic INCR)                         │    │
│  │  ├── Server health state (ephemeral)                           │    │
│  │  └── Celery broker + result backend                            │    │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Background Workers                          │    │
│  │                                                                │    │
│  │  Celery Workers:                                               │    │
│  │  ├── Approval notifier (email/Slack/webhook)                   │    │
│  │  ├── Audit export generator (CSV/JSON)                         │    │
│  │  ├── Alert delivery (email/Slack/webhook)                      │    │
│  │  ├── Server health checker (periodic ping /tools/list)        │    │
│  │  └── Audit log retention cleanup                               │    │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Telemetry                                   │    │
│  │  Prometheus metrics   OpenTelemetry traces   structlog        │    │
│  └────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐   ┌──────────┐   ┌──────────────┐
   │PostgreSQL│   │  Redis   │   │ OPA Server   │
   │ / SQLite │   │          │   │ (policy eval)│
   └─────────┘   └──────────┘   └──────────────┘
```

### 1.2 Data Center Deployment at Scale

```
                              ┌─────────────────────────────────┐
                              │         Agent Traffic            │
                              │  (thousands of agents across     │
                              │   multiple teams/environments)   │
                              └───────────────┬─────────────────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │   Load Balancer    │
                                    │  (TLS termination,  │
                                    │   health checks,    │
                                    │   rate limiting)    │
                                    └─────────┬─────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
          ┌─────────▼─────────┐   ┌──────────▼──────────┐   ┌─────────▼─────────┐
          │  Fabric API       │   │  Fabric API          │   │  Fabric API       │
          │  Instance 1       │   │  Instance 2          │   │  Instance 3       │
          │  (us-east-1a)     │   │  (us-east-1b)        │   │  (us-east-1c)     │
          │                   │   │                      │   │                   │
          │  FastAPI + OPA    │   │  FastAPI + OPA       │   │  FastAPI + OPA    │
          │  SDK (embedded)   │   │  SDK (embedded)      │   │  SDK (embedded)   │
          └─────────┬─────────┘   └──────────┬──────────┘   └─────────┬─────────┘
                    │                         │                         │
                    └─────────────────────────┼─────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
          ┌─────────▼─────────┐   ┌──────────▼──────────┐   ┌─────────▼─────────┐
          │  Celery Worker    │   │  Celery Worker       │   │  Celery Beat      │
          │  Pool (3 workers) │   │  Pool (3 workers)    │   │  (scheduler)      │
          │                   │   │                      │   │                   │
          │  • approval       │   │  • approval          │   │  • health checks  │
          │    notifications  │   │    notifications     │   │    (every 30s)    │
          │  • audit export   │   │  • audit export      │   │  • retention      │
          │  • alert delivery │   │  • alert delivery    │   │    cleanup (daily) │
          └─────────┬─────────┘   └──────────┬──────────┘   └─────────┬─────────┘
                    │                         │                         │
                    └─────────────────────────┼─────────────────────────┘
                                              │
          ┌───────────────────────────────────┼───────────────────────┐
          │                                   │                       │
┌─────────▼─────────┐  ┌──────────────────────▼───────┐  ┌───────────▼───────────┐
│  PostgreSQL       │  │  Redis Cluster                 │  │  OPA Server          │
│  Primary          │  │                                │  │  (optional external) │
│  (us-east-1a)     │  │  • Agent sessions (TTL)         │  │                      │
│                   │  │  • Rate limit counters          │  │  • Rego policy files │
│  ┌─────────────┐  │  │  • Server health state          │  │  • Policy bundles    │
│  │ Read Replica│  │  │  • Celery broker + backend      │  │  • Decision logs     │
│  │ (us-east-1b)│  │  │  • Leader election lock         │  └───────────────────────┘
│  └─────────────┘  │  │  (for health check singleton)   │
│                   │  │                                │
│  • PITR backups   │  │  Sentinel for HA               │
│  • WAL archiving  │  └────────────────────────────────┘
└───────────────────┘
          │
┌─────────▼──────────────────────────────────────────────────────────┐
│                      Monitoring Stack                               │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │Prometheus│  │ Grafana  │  │  Tempo   │  │AlertMgr  │           │
│  │(metrics) │  │(dashboards)│ │(traces) │  │(alerts)  │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└────────────────────────────────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
          ┌─────────▼─────────┐   ┌──────────▼──────────┐   ┌─────────▼─────────┐
          │  MCP Servers      │   │  MCP Servers         │   │  MCP Servers      │
          │  (Platform Team)  │   │  (Security Team)     │   │  (Data Team)      │
          │                   │   │                      │   │                   │
          │  • Code Search    │   │  • Vuln Scanner      │   │  • Database Query  │
          │  • Docs Search    │   │  • Dep Audit         │   │  • Data Catalog   │
          │  • Deployment     │   │  • Secret Detect     │   │                   │
          │  • CI/CD Status   │   │                      │   │  team:data         │
          │  • Git History    │   │  team:security       │   │                   │
          │                   │   │                      │   │                   │
          │  team:platform    │   │                      │   │                   │
          └───────────────────┘   └──────────────────────┘   └───────────────────┘
```

### 1.3 Request Lifecycle (Detailed)

```
Agent sends POST /capability/request
    Header: Authorization: Bearer fcp_xxxx
    Header: Accept: application/vnd.fabric.v1+json
    Body: { "capability": "code:blameless-diff", "params": {...} }
        │
        ▼
┌─────────────────────────────────────────────┐
│ Middleware: AuthMiddleware                   │
│ 1. Extract token from Authorization header   │
│ 2. Hash token, lookup in Redis (hot path)   │
│ 3. Fallback: DB lookup + cache in Redis     │
│ 4. Set request.state.agent_identity          │
│ 5. Set request.state.agent_class             │
│ 6. Set request.state.team_namespace          │
│ 7. 401 if invalid/expired/revoked           │
├─────────────────────────────────────────────┤
│ Middleware: RateLimitMiddleware             │
│ 1. Key: fcp:ratelimit:{agent_id}:{minute}   │
│ 2. Redis INCR, check against limit          │
│ 3. 429 if exceeded, with Retry-After        │
├─────────────────────────────────────────────┤
│ Middleware: TenantMiddleware                │
│ 1. Set request.state.tenant_filter          │
│ 2. All DB queries auto-scoped to namespace  │
├─────────────────────────────────────────────┤
│ Route Handler: POST /capability/request     │
│ 1. Validate body against Pydantic schema     │
│ 2. Call RoutingService.execute()            │
├─────────────────────────────────────────────┤
│ RoutingService.execute()                    │
│                                             │
│ Step 1: Resolve capability                  │
│   SELECT * FROM capabilities                │
│   WHERE name = 'code:blameless-diff'        │
│     OR aliases @> '["code:blameless-diff"]' │
│   LIMIT 1                                   │
│   → 404 if not found                        │
│                                             │
│ Step 2: Get candidate servers               │
│   SELECT sm.*, st.tool_name, st.input_schema│
│   FROM capability_mappings cm               │
│   JOIN server_tools st ON ...               │
│   JOIN mcp_servers s ON ...                 │
│   WHERE cm.capability_id = $cap_id          │
│     AND s.health_status != 'unhealthy'      │
│     AND s.decommissioned_at IS NULL         │
│   → 503 if no candidates (fabric degraded)  │
│                                             │
│ Step 3: Apply routing rules                 │
│   SELECT * FROM routing_rules               │
│   WHERE capability_id = $cap_id             │
│   ORDER BY priority                         │
│   Filter candidates by rule conditions      │
│   (e.g., "file_pattern in params")          │
│                                             │
│ Step 4: Evaluate policy (OPA)               │
│   POST http://localhost:8181/v1/data/       │
│        fabric/policy/allow                  │
│   Body: {                                   │
│     "input": {                              │
│       "agent_class": "incident-responder",  │
│       "capability": "code:blameless-diff",  │
│       "server_id": "uuid",                  │
│       "team_namespace": "team:platform"     │
│     }                                       │
│   }                                         │
│   Response: { "result": { "allow": true,   │
│              "trust_level": "trusted" } }   │
│   → Filter candidates to allowed only      │
│   → 403 if all denied                       │
│   → 202 if approval-gated                   │
│                                             │
│ Step 5: Rank candidates                     │
│   Score = match_quality × policy × priority │
│   Tiebreaker: latency (from Redis health)   │
│   Select top candidate                       │
│                                             │
│ Step 6: Call MCP server                     │
│   mcp_client.call_tool(                     │
│     server=selected_server,                 │
│     tool=mapped_tool,                       │
│     arguments=translated_params             │
│   )                                         │
│   Timeout: 5s with 1 retry                 │
│   → If timeout/error: goto fallback        │
│                                             │
│ Step 7: Fallback (if primary fails)         │
│   Mark server as degraded (Redis)           │
│   Log degradation event (DB)                │
│   Select next candidate from step 5         │
│   Call fallback server                      │
│   Record fallback in response metadata      │
│   Check alert threshold → Celery task       │
│                                             │
│ Step 8: Normalize response                  │
│   Apply output_mapping from capability      │
│   mapping entry                             │
│   Ensure response matches normalized        │
│   output schema                              │
│                                             │
│ Step 9: Audit                               │
│   INSERT INTO audit_events (                │
│     event_type='capability_request',        │
│     actor_type='agent',                     │
│     actor_id=$agent_id,                     │
│     details={ routing, latency, server }    │
│   )                                         │
│                                             │
│ Step 10: Return                             │
│   200 + normalized response                 │
│     + routing metadata                      │
└─────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer | Choice | Version | Rationale |
|---|---|---|---|
| **Language** | Python | 3.12+ | Async support, MCP SDK compatibility, ecosystem |
| **API framework** | FastAPI | 0.115+ | Native async, auto OpenAPI, Pydantic v2, dependency injection |
| **ORM** | SQLAlchemy | 2.0+ | Async support, Alembic migrations, mature |
| **Validation** | Pydantic | 2.x | Request/response validation, JSON Schema generation |
| **Database (local)** | SQLite | 3.45+ | Zero-dependency local dev via aiosqlite |
| **Database (prod)** | PostgreSQL | 16+ | JSONB, full-text search, concurrent access, PITR |
| **Cache / broker** | Redis | 7+ | Sessions, rate limiting, health state, Celery broker |
| **MCP client** | `mcp` (Anthropic SDK) | latest | Official SDK, protocol compliance, tools/list + tools/call |
| **Policy engine** | OPA (Open Policy Agent) | 0.68+ | Rego policies, decision logs, bundle API, industry standard |
| **Task queue** | Celery | 5.4+ | Retries, scheduling, monitoring, Redis broker |
| **UI framework** | React | 18+ | Component model, ecosystem |
| **UI language** | TypeScript | 5.x | Type safety for API contracts |
| **UI build** | Vite | 5.x | Fast dev server, optimized builds |
| **UI styling** | Tailwind CSS | 3.x | Utility-first, responsive, themeable |
| **UI server state** | TanStack Query | 5.x | Caching, refetching, optimistic updates |
| **UI local state** | React Context | — | Modals, filters, UI-only state |
| **Package mgmt** | Poetry | 1.8+ | Lockfile, dependency groups, deterministic builds |
| **Testing** | Pytest + pytest-asyncio | 8.x | Async test support, fixtures, coverage |
| **Test HTTP** | httpx | 0.27+ | Async HTTP client for integration tests |
| **Metrics** | prometheus_client | 0.21+ | Counter, Histogram, Gauge for API metrics |
| **Tracing** | OpenTelemetry SDK | 1.x | Span export to Tempo/Jaeger |
| **Logging** | structlog | 24.x | Structured JSON logging, context binding |
| **Linting** | Ruff | 0.5+ | Fast Python linter + formatter |
| **Linting (TS)** | ESLint + Prettier | latest | Standard TypeScript tooling |
| **Container** | Docker + Compose | latest | Dev parity, CI, production images |

---

## 3. Database Schema

### 3.1 Dual Database Strategy

Fabric supports two database backends via SQLAlchemy with **zero code branches**:

- **Local dev (SQLite):** Set `DATABASE_URL=sqlite+aiosqlite:///fabric.db`. No Docker required. All features work except concurrent multi-instance deployments.
- **Production (PostgreSQL):** Set `DATABASE_URL=postgresql+asyncpg://...`. Full concurrent access, JSONB indexing, PITR backups.

```python
# api/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///fabric.db"
    redis_url: str = "redis://localhost:6379/0"
    opa_url: str = "http://localhost:8181"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    environment: str = "development"  # development | production
    log_level: str = "INFO"
```

### 3.2 Full Schema

(All tables from spec.md v1.0 preserved, with these additions for the new tech choices:)

#### 3.18 `capability_aliases`

```sql
CREATE TABLE capability_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capability_id UUID NOT NULL REFERENCES capabilities(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL UNIQUE,    -- e.g., 'repo:search' → maps to 'code:search'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_aliases_capability ON capability_aliases(capability_id);
```

#### 3.19 `opa_policy_versions`

```sql
CREATE TABLE opa_policy_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(50) NOT NULL,
    bundle_hash VARCHAR(64),
    deployed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deployed_by VARCHAR(255),
    rego_content TEXT NOT NULL
);
```

#### 3.20 `background_tasks`

```sql
CREATE TABLE background_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    celery_task_id VARCHAR(255),
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    params JSONB,
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_bgtasks_status ON background_tasks(status);
CREATE INDEX idx_bgtasks_celery ON background_tasks(celery_task_id);
```

---

## 4. API Contract

### 4.1 Versioning Strategy

API versioning uses **custom media type in the Accept header**:

```
Accept: application/vnd.fabric.v1+json
```

The API returns the version in the response:

```
Content-Type: application/vnd.fabric.v1+json
Fabric-API-Version: v1
```

Without a version header, the API defaults to the latest stable version and returns a warning header:

```
Fabric-API-Warning: "No version specified, defaulting to v1. Specify Accept: application/vnd.fabric.v1+json"
```

### 4.2 Common Headers

| Header | Direction | Purpose |
|---|---|---|
| `Authorization: Bearer <token>` | Request | Agent authentication |
| `Accept: application/vnd.fabric.v1+json` | Request | API version selection |
| `Fabric-API-Version: v1` | Response | Confirmed API version |
| `Fabric-Request-Id: uuid` | Both | Request tracing |
| `Retry-After: 5` | Response | Rate limit / degradation retry hint |
| `Fabric-Routing-Server: server-name` | Response | Which server handled the request |
| `Fabric-Routing-Reason: string` | Response | Why this server was selected |
| `Fabric-Routing-Fallback: true` | Response | Indicates fallback was used |

### 4.3 All Endpoints

(All endpoints from spec.md v1.0 preserved, with these additions:)

#### Agent Capability Change Webhook Registration

```
POST /agents/{agent_id}/webhooks
Body: {
    "url": "https://igor.internal/fabric-events",
    "events": ["capability_added", "capability_deprecated", "capability_schema_changed"]
}
Response 201: { "id": "uuid", "webhook_secret": "whsec_xxx" }
```

#### Policy Bundle Upload (OPA)

```
POST /admin/policies/bundle
Body: { "rego_content": "package fabric.policy\n\n..." }
Response 201: { "version": "v3", "deployed": true }
```

---

## 5. OPA Policy Engine Integration

### 5.1 Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Fabric API      │────▶│  OPA SDK Client  │────▶│  OPA Server     │
│  (FastAPI)       │     │  (embedded)      │     │  (localhost:8181)│
│                  │     │                  │     │                  │
│  PolicyService   │     │  opa.evaluate()  │     │  Rego policies   │
│  .evaluate()     │     │  decision_log()  │     │  Decision log    │
└─────────────────┘     └──────────────────┘     └──────────────────┘
```

OPA runs **embedded** (as a subprocess or sidecar) in development — single binary, no external dependency. In production, it can be an external OPA server for independent scaling and policy management.

### 5.2 Rego Policies

```rego
package fabric.policy

# Default: deny all
default allow := false

# Trust level hierarchy
trust_levels := {
    "trusted": 3,
    "restricted": 2,
    "approval-gated": 1,
    "unreviewed": 0
}

# Agent class → minimum required trust level
class_min_trust := {
    "agent:admin": 3,
    "agent:incident-responder": 2,
    "agent:deploy-monitor": 2,
    "agent:code-reviewer": 1,
    "agent:developer": 1,
    "agent:new-hire": 0
}

# Main allow rule
allow {
    agent_trust := class_min_trust[input.agent_class]
    server_trust := trust_levels[input.server_trust_level]
    server_trust >= agent_trust
}

# Approval-gated: allowed but requires human approval
approval_required {
    input.server_trust_level == "approval-gated"
    input.agent_class != "agent:admin"
}

# Decision output
result := {
    "allow": allow,
    "approval_required": approval_required,
    "trust_level": input.server_trust_level,
    "agent_class": input.agent_class
}
```

### 5.3 Policy Evaluation Flow

```python
# api/services/policy_service.py
from opa_client import OPAClient

class PolicyService:
    def __init__(self, opa_client: OPAClient):
        self.opa = opa_client

    async def evaluate(
        self,
        agent_class: str,
        server_id: str,
        capability: str,
        team_namespace: str
    ) -> PolicyDecision:
        input_data = {
            "input": {
                "agent_class": agent_class,
                "server_id": server_id,
                "capability": capability,
                "team_namespace": team_namespace
            }
        }
        result = await self.opa.evaluate("fabric/policy/allow", input_data)
        
        # Log decision for audit
        await self.opa.log_decision(input_data, result)
        
        return PolicyDecision(
            allow=result["allow"],
            approval_required=result.get("approval_required", False),
            trust_level=result.get("trust_level", "unreviewed")
        )
```

---

## 6. Background Tasks (Celery)

### 6.1 Task Definitions

```python
# api/tasks.py
from celery import Celery

celery_app = Celery(
    "fabric",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/2"
)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def notify_approval_request(self, approval_id: str):
    """Send email/Slack/webhook for new approval request."""
    ...

@celery_app.task(bind=True, max_retries=3)
def deliver_alert(self, alert_event_id: str):
    """Deliver alert via configured channels."""
    ...

@celery_app.task
def generate_audit_export(export_id: str):
    """Generate CSV/JSON audit export file."""
    ...

@celery_app.task(bind=True, max_retries=2)
def health_check_server(self, server_id: str):
    """Ping MCP server /tools/list, update health state."""
    ...

@celery_app.task
def cleanup_audit_logs():
    """Remove audit events older than retention window."""
    ...

@celery_app.task
def check_alert_thresholds():
    """Evaluate alert rules against recent metrics."""
    ...
```

### 6.2 Celery Beat Schedule

```python
# api/config.py
CELERY_BEAT_SCHEDULE = {
    "health-check-all-servers": {
        "task": "api.tasks.health_check_all_servers",
        "schedule": 30.0,  # every 30 seconds
    },
    "cleanup-audit-logs": {
        "task": "api.tasks.cleanup_audit_logs",
        "schedule": crontab(hour=3, minute=0),  # daily at 3 AM
    },
    "check-alert-thresholds": {
        "task": "api.tasks.check_alert_thresholds",
        "schedule": 60.0,  # every minute
    },
}
```

---

## 7. Component Interfaces

### 7.1 RegistryService

```python
class RegistryService:
    async def register(self, name: str, endpoint: str, **meta) -> MCPServer:
        """Register a server, inspect /tools/list, create Server + Tool records, return full server."""
    
    async def inspect(self, server_id: UUID) -> InspectionResult:
        """Re-fetch /tools/list, diff against tool_versions, return changes."""
    
    async def decommission(self, server_id: UUID, phase: str, replacement_id: UUID | None) -> DecommissionResult:
        """Begin phased decommission, return dependencies and migration plan."""
    
    async def list_servers(self, team: str | None, trust: str | None, health: str | None) -> list[MCPServer]:
        """Filtered server listing with tenant scoping."""
    
    async def get_server(self, server_id: UUID) -> MCPServerDetail:
        """Full server detail with tools, routing rules, trust assignments."""
```

### 7.2 CapabilityService

```python
class CapabilityService:
    async def create(self, name: str, domain: str, **schema) -> Capability:
        """Create a new capability with normalized input/output schemas."""
    
    async def map_tool(self, capability_id: UUID, server_id: UUID, tool_name: str, **mapping) -> CapabilityMapping:
        """Map a server tool to a capability. Trigger conflict detection."""
    
    async def resolve(self, name: str) -> Capability:
        """Resolve a capability name (exact match or alias). Raise 404 if not found."""
    
    async def detect_conflicts(self, capability_id: UUID) -> list[Conflict]:
        """Find servers with overlapping capability mappings."""
    
    async def deprecate(self, capability_id: UUID, grace_days: int, guidance: str) -> Capability:
        """Mark capability as deprecated with grace period."""
    
    async def add_alias(self, capability_id: UUID, alias: str) -> CapabilityAlias:
        """Add an alias for capability name resolution."""
```

### 7.3 RoutingService

```python
class RoutingService:
    async def execute(self, capability_name: str, params: dict, agent_identity: AgentIdentity) -> RouteResult:
        """Full routing pipeline: resolve → policy → select → call → normalize → audit."""
    
    async def execute_batch(self, requests: list[CapabilityRequest], agent_identity: AgentIdentity) -> BatchResult:
        """Execute multiple capability requests in parallel."""
```

### 7.4 PolicyService

```python
class PolicyService:
    async def evaluate(self, agent_class: str, server_id: UUID, capability: str, team: str) -> PolicyDecision:
        """Evaluate via OPA. Return allow/deny/approval_required."""
    
    async def deploy_bundle(self, rego_content: str, deployed_by: str) -> PolicyBundleVersion:
        """Deploy new OPA policy bundle, version it in DB."""
```

### 7.5 SandboxService

```python
class SandboxService:
    async def create_sandbox(self, trust_change: TrustChange) -> Sandbox:
        """Create a sandbox evaluation for a proposed trust change."""
    
    async def evaluate_request(self, sandbox_id: UUID, request: CapabilityRequest) -> SandboxEvaluation:
        """Shadow-evaluate a real request against sandbox policy."""
    
    async def get_results(self, sandbox_id: UUID) -> SandboxResult:
        """Aggregate sandbox results: would_approve, would_deny, false_positives."""
```

### 7.6 MCPClient

```python
class MCPClient:
    async def list_tools(self, endpoint: str, timeout: float = 5.0) -> list[ToolDefinition]:
        """Call /tools/list on an MCP server, return parsed tool definitions."""
    
    async def call_tool(self, endpoint: str, tool_name: str, arguments: dict, timeout: float = 5.0) -> ToolResponse:
        """Call /tools/call on an MCP server, return raw response."""
    
    async def diff_tools(self, endpoint: str, previous_tools: list[ToolDefinition]) -> ToolDiff:
        """Compare current /tools/list against previous, return additions/removals/changes."""
```

---

## 8. Error Handling Patterns

### 8.1 Error Response Format

All errors return a consistent JSON structure:

```json
{
    "error": "error_code",
    "message": "Human-readable description",
    "details": {},
    "request_id": "uuid"
}
```

### 8.2 Error Catalog

| HTTP | Error Code | Scenario | Journey |
|---|---|---|---|
| 400 | `invalid_parameter` | Malformed capability request params | 13 |
| 401 | `invalid_token` | Missing/expired/revoked agent token | 29 |
| 401 | `token_expired` | Token past expiration with no grace period | 29 |
| 403 | `access_denied` | Agent class not authorized for capability | 2 |
| 403 | `namespace_restricted` | Agent outside allowed team namespace | 20 |
| 404 | `capability_not_found` | Requested capability doesn't exist | 13 |
| 404 | `server_not_found` | Referenced server doesn't exist | — |
| 409 | `capability_conflict` | Two servers claim same capability | 9 |
| 409 | `schema_breaking_change` | Server upgrade contains breaking changes | 10 |
| 422 | `validation_error` | Request body fails Pydantic validation | — |
| 429 | `rate_limited` | Agent exceeded request limit | 29 |
| 503 | `fabric_degraded` | Fabric internal error (DB/Redis down) | 13 |
| 503 | `no_healthy_server` | All candidate servers unhealthy | 6 |

---

## 9. Security Model

### 9.1 Agent Authentication

```
Agent identity token: fcp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                          │
                          └── 4-char prefix for UI display
                              Remaining chars: random + hashed

Storage:
- Token hash: bcrypt(salt=12, token) → stored in DB
- Token prefix: first 4 chars → stored in DB for display
- Full token: returned ONCE at creation time, never stored
```

### 9.2 Admin Authentication

```
Admin user flow:
1. Invite: admin creates user with email + role
2. Setup: user receives invite link, sets password
3. Login: password + optional TOTP (MFA)
4. Session: JWT with 8h expiry, stored in Redis
5. Logout: Redis key deleted, JWT blacklisted
```

### 9.3 Threat Mitigations

| Threat | Mitigation |
|---|---|
| Token theft | Tokens can be revoked immediately. Rotate with grace period. |
| Brute force login | 5 failed attempts → 15 min account lock. Rate limit on /auth/login |
| SQL injection | SQLAlchemy parameterized queries — no raw SQL |
| Capability enumeration | Rate limit per agent. Audit log captures enumeration attempts |
| Cross-team access | TenantMiddleware enforces team_namespace on every DB query |
| Audit tampering | Append-only audit_events table. No UPDATE or DELETE on audit rows |
| OPA bypass | Fabric API enforces OPA evaluation — agents cannot skip it |

---

## 10. Configuration Management

### 10.1 Environment Variables

| Variable | Default (dev) | Production | Purpose |
|---|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///fabric.db` | `postgresql+asyncpg://...` | Database connection |
| `REDIS_URL` | `redis://localhost:6379/0` | `redis://redis-cluster:6379/0` | Redis connection |
| `OPA_URL` | `http://localhost:8181` | `http://opa.fabric.svc:8181` | OPA server URL |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Same as Redis | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Same as Redis | Celery results |
| `SECRET_KEY` | `dev-secret-change-me` | Generated secret | JWT signing |
| `ENVIRONMENT` | `development` | `production` | Environment mode |
| `LOG_LEVEL` | `DEBUG` | `INFO` | Logging level |
| `AUDIT_RETENTION_DAYS` | `90` | `90` | Audit log retention |
| `SERVER_HEALTH_INTERVAL` | `30` | `30` | Health check interval (seconds) |
| `DEFAULT_RATE_LIMIT` | `100` | `100` | Default requests/min per agent |

### 10.2 Feature Flags

```python
FEATURE_FLAGS = {
    "enable_streaming": False,        # MCP streaming responses (v0.3.0)
    "enable_federation": False,       # Cross-Fabric sharing (future)
    "require_mfa_for_admins": False,  # Enforce MFA for admin role
    "enable_fuzzy_capability_match": False,  # Semantic capability matching
}
```

---

## 11. Test Strategy

### 11.1 Test Pyramid

```
        ┌──────────┐
        │   E2E    │  5%  — Full docker-compose, real OPA, Celery, PostgreSQL
        │   (10)   │       Register server → capability request → audit
        ├──────────┤
        │Integration│ 20%  — FastAPI TestClient + test DB + mock MCP server
        │   (40)   │       Policy evaluation, routing, approval flow, fallback
        ├──────────┤
        │   Unit   │ 75%  — Service layer, OPA rego tests, schema validation,
        │  (150)   │       capability resolution, normalization, diff logic
        └──────────┘
```

### 11.2 Test Fixtures

```python
# tests/conftest.py
@pytest.fixture
async def app():
    """FastAPI app with SQLite test DB, mock OPA, mock Redis."""
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        environment="testing"
    )
    app = create_app(settings)
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def mock_mcp_server():
    """In-process FastAPI app implementing MCP /tools/list and /tools/call."""
    ...

@pytest.fixture
def agent_token(app, agent_class_name):
    """Create test agent identity, return bearer token."""
    ...
```

### 11.3 OPA Policy Tests

```rego
# tests/policies/test_policy.rego
test_allow_trusted_server_for_incident_responder {
    allow with input as {
        "agent_class": "agent:incident-responder",
        "server_trust_level": "trusted",
        "capability": "code:search",
        "team_namespace": "team:platform"
    }
}

test_deny_unreviewed_server_for_new_hire {
    not allow with input as {
        "agent_class": "agent:new-hire",
        "server_trust_level": "unreviewed"
    }
}

test_approval_required_for_gated_capability {
    approval_required with input as {
        "agent_class": "agent:code-reviewer",
        "server_trust_level": "approval-gated"
    }
}
```

---

## 12. Project Configuration Files

### 12.1 pyproject.toml

```toml
[tool.poetry]
name = "mcp-fabric"
version = "0.1.0"
description = "Composable tool mesh for MCP ecosystems"
authors = ["Debashish Ghosal <debashish@ghosal.dev>"]
license = "MIT"
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.32"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
aiosqlite = "^0.20"
asyncpg = "^0.29"
alembic = "^1.13"
pydantic = "^2.9"
pydantic-settings = "^2.6"
redis = "^5.2"
celery = {extras = ["redis"], version = "^5.4"}
httpx = "^0.27"
mcp = "^1.0"
opa-client = "^0.5"          # Python client for OPA REST API
prometheus-client = "^0.21"
opentelemetry-sdk = "^1.28"
opentelemetry-instrumentation-fastapi = "^0.49"
structlog = "^24.4"
python-jose = {extras = ["cryptography"], version = "^3.3"}
passlib = {extras = ["bcrypt"], version = "^1.7"}
pyotp = "^2.9"                # TOTP for admin MFA

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-asyncio = "^0.24"
pytest-cov = "^5.0"
httpx = "^0.27"
ruff = "^0.6"
alembic = "^1.13"

[tool.poetry.group.ui.dependencies]
# UI deps managed via package.json — not Poetry

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## 13. Milestone Breakdown (Updated)

### v0.1.0 — Core Routing (Weeks 1-4)

**Deliverables:**
- [x] Server registry — register, inspect, list, get (Journey 1)
- [x] Capability catalog — create, map tools, list, aliases (Journey 27)
- [x] Routing engine — single + batch capability request (Journeys 2, 23)
- [x] OPA policy engine — allow/deny/approve-gated, Rego policies (Journey 2)
- [x] Agent auth — token create, connect, capability surface (Journeys 5, 21, 29)
- [x] Capability discovery — agent gets full schema at startup (Journey 22)
- [x] Error handling — structured errors for all scenarios (Journey 13)
- [x] Audit pipeline — log requests/denials/policy changes (Journey 4)
- [x] Admin UI — server inventory, capability browser, basic audit viewer (Journeys 1, 8)
- [x] Health endpoint + Prometheus metrics + OpenTelemetry traces (Journey 28)
- [x] SQLite for local dev, PostgreSQL for production
- [x] Docker Compose + Poetry + Makefile
- [x] Test suite (P0 scenarios)

### v0.2.0 — Governance (Weeks 5-8)

- [ ] Capability packs — create, assign to classes (Journey 3)
- [ ] Conflict detection + resolution (Journey 9)
- [ ] Routing rules — explicit preferences (Journey 9)
- [ ] Server decommission — phased sunset (Journey 11)
- [ ] Capability deprecation — grace period (Journey 12)
- [ ] Schema diff on re-inspect (Journey 10)
- [ ] Policy sandbox — shadow evaluation (Journey 19)
- [ ] Incremental migration support (Journey 15)

### v0.3.0 — Scale (Weeks 9-12)

- [ ] Fallback chain — degraded server routing (Journey 6)
- [ ] Alerting engine — degradation, unreviewed, denial spikes (Journeys 4, 6, 28)
- [ ] Approval-gated capabilities — human-in-the-loop (Journey 7)
- [ ] Multi-team namespaces — row-level filtering (Journey 20)
- [ ] Admin user management — roles, MFA, deactivation (Journey 26)
- [ ] Audit export — structured JSON/CSV (Journey 18)
- [ ] Token rotation with grace period (Journey 29)
- [ ] Fabric backup/restore tooling (Journey 24)

### v0.4.0 — Production (Weeks 13-16)

- [ ] Blue-green Fabric upgrade — zero-downtime (Journey 25)
- [ ] Pre-built Grafana dashboard JSON (Journey 28)
- [ ] IP allow-listing for admin UI (Journey 29)
- [ ] Analytics and usage heatmaps
- [ ] Reference MCP server integrations
- [ ] Performance benchmarks
- [ ] Horizontal scaling guide

---

## 14. First-Time Deployment Procedure (Journey 16)

### 14.1 Zero-to-First-Request Walkthrough

```bash
# 1. Start Fabric (SQLite mode — no Docker)
poetry install
poetry run uvicorn api.main:app --reload
# API: http://localhost:8000, Docs: http://localhost:8000/docs

# 2. Register first MCP server
curl -X POST http://localhost:8000/v1/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "KB Server",
    "endpoint": "http://localhost:3001",
    "owner_team": "platform",
    "labels": ["knowledge", "internal"]
  }'
# Response includes auto-discovered tools from /tools/list

# 3. Create first capability
curl -X POST http://localhost:8000/v1/capabilities \
  -H "Content-Type: application/json" \
  -d '{
    "name": "knowledge:search",
    "domain": "knowledge",
    "description": "Search documentation and knowledge base"
  }'

# 4. Map tool to capability
curl -X POST http://localhost:8000/v1/capabilities/{cap_id}/mappings \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "{server_id}",
    "tool_name": "search_kb",
    "is_primary": true
  }'

# 5. Create agent class
curl -X POST http://localhost:8000/v1/agent-classes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "agent:developer",
    "description": "Developer coding assistant"
  }'

# 6. Set trust assignment
curl -X POST http://localhost:8000/v1/agent-classes/{class_id}/trust \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "{server_id}",
    "trust_level": "trusted"
  }'

# 7. Create agent identity token
curl -X POST http://localhost:8000/v1/admin/agent-identities \
  -H "Content-Type: application/json" \
  -d '{
    "name": "dev-agent-01",
    "agent_class_id": "{class_id}"
  }'
# Response includes token — SAVE IT. It's shown only once.

# 8. Agent: connect and discover capabilities
curl -X POST http://localhost:8000/v1/auth/connect \
  -H "Authorization: Bearer fcp_xxxxxxxxxxxx" \
  -H "Accept: application/vnd.fabric.v1+json"
# Response: agent_id, agent_class, capability_surface

curl http://localhost:8000/v1/capabilities/available \
  -H "Authorization: Bearer fcp_xxxxxxxxxxxx" \
  -H "Accept: application/vnd.fabric.v1+json"
# Response: full capability schemas

# 9. Agent: make first capability request
curl -X POST http://localhost:8000/v1/capability/request \
  -H "Authorization: Bearer fcp_xxxxxxxxxxxx" \
  -H "Accept: application/vnd.fabric.v1+json" \
  -H "Content-Type: application/json" \
  -d '{"capability": "knowledge:search", "params": {"query": "deployment runbook"}}'
# Response: normalized search results, routed through KB Server

# 10. Verify: check audit log
curl http://localhost:8000/v1/audit?actor_id=dev-agent-01 \
  -H "Accept: application/vnd.fabric.v1+json"
# Response: capability_request event with routing detail

# 🎉 Fabric is operational. First request routed, audited, policy-checked.
```

### 14.2 Empty State UX

When Fabric starts with zero data:
- `GET /servers` returns `{ "servers": [], "total": 0 }` — no 404
- Admin UI shows onboarding prompt: "Register your first MCP server"
- `POST /auth/connect` returns 401 if no tokens exist
- Health endpoint returns healthy (even with empty DB)

---

## 15. Incremental Migration Strategy (Journey 15)

### 15.1 Dual-Mode Routing

During migration, agents can route **some capabilities through Fabric and others through direct MCP connections**. Fabric supports this with a per-capability routing mode.

```
Agent Configuration (dual-mode):
{
    "fabric_enabled": true,
    "fabric_endpoint": "http://fabric:8000",
    "migration_state": {
        "code:search": "fabric",           // routed through Fabric
        "code:blameless-diff": "fabric",   // routed through Fabric
        "knowledge:doc-search": "fabric",  // routed through Fabric
        "deployment:status": "direct",     // still direct connection
        "incident:create": "direct",       // still direct connection
        "vulnerability:scan": "direct"     // not yet registered in Fabric
    }
}
```

### 15.2 Agent-Side Implementation

```python
# Agent capability client with dual-mode support
class CapabilityClient:
    def __init__(self, fabric_url: str | None, migration_state: dict):
        self.fabric_client = FabricClient(fabric_url) if fabric_url else None
        self.direct_clients = {...}  # existing direct MCP connections
        self.migration_state = migration_state

    async def request(self, capability: str, params: dict) -> Response:
        mode = self.migration_state.get(capability, "direct")

        if mode == "fabric" and self.fabric_client:
            return await self.fabric_client.request(capability, params)
        elif mode == "direct":
            return await self.direct_client(capability).call(params)
        else:
            raise ValueError(f"Unknown migration mode: {mode}")
```

### 15.3 Fabric-Side Migration API

```
GET /v1/admin/migration/status
Response 200: {
    "total_servers": 8,
    "migrated_servers": 6,
    "pending_servers": 2,
    "migration_started_at": "2026-07-22",
    "server_status": [
        {"name": "Docs Search", "migrated": true, "migrated_at": "..."},
        {"name": "Git History", "migrated": true, "migrated_at": "..."},
        {"name": "Deployment", "migrated": false, "reason": "pending trust review"},
        {"name": "Internal Tooling", "migrated": false, "reason": "complex auth"}
    ]
}
```

### 15.4 Migration Validation Checklist

Before marking a server as "migrated":
- [ ] Server registered in Fabric with correct endpoint
- [ ] All tools imported and mapped to capabilities
- [ ] Trust level assigned for relevant agent classes
- [ ] Capability request test: same input → comparable output (direct vs Fabric)
- [ ] Latency check: Fabric overhead < 50ms
- [ ] Audit log confirms requests are captured
- [ ] Agents switched to `"fabric"` mode for this capability
- [ ] 3-day validation window passed with no anomalies

---

## 16. Disaster Recovery (Journey 24)

### 16.1 Backup Strategy

Fabric state is fully contained in PostgreSQL. Backup strategy follows standard PostgreSQL patterns:

```
Backup Schedule:
├── Full backup: every 6 hours (pg_dump or pg_basebackup)
├── WAL archiving: continuous (write-ahead log shipping)
└── Point-in-time recovery window: up to the last archived WAL segment

Retention:
├── Daily backups: 30 days
├── Weekly backups: 12 weeks
└── Monthly backups: 12 months
```

### 16.2 Backup Configuration

```yaml
# PostgreSQL configuration for PITR
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'pgbackrest --stanza=fabric archive-push %p'
max_wal_senders = 3

# pgbackrest.conf
[fabric]
pg1-path=/var/lib/postgresql/data
repo1-path=/backups/fabric
repo1-retention-full=4
repo1-retention-diff=14
```

### 16.3 Fabric Admin CLI (restore tool)

```bash
# Check backup status
fabric-admin backup status
# Output: Latest full backup: 2026-07-22 06:00 UTC (age: 2h)
#         WAL archive lag: 0 seconds
#         Next scheduled: 2026-07-22 12:00 UTC

# Trigger manual backup
fabric-admin backup create --type full

# List available backups
fabric-admin backup list
# Output:
#   backup-2026-07-22-0600  full   2.3 GB  healthy
#   backup-2026-07-22-0000  full   2.1 GB  healthy
#   backup-2026-07-21-1800  full   2.0 GB  healthy

# Restore from latest backup
fabric-admin restore latest \
  --target-db-url "postgresql+asyncpg://new-host:5432/mcp_fabric" \
  --validate
# Steps:
#   1. Create empty database at target
#   2. Restore full backup
#   3. Apply WAL segments up to latest
#   4. Validate: check table counts, foreign keys, agent token hashes
#   5. Output: restore summary + validation report

# Point-in-time restore (recover to specific timestamp)
fabric-admin restore point-in-time \
  --timestamp "2026-07-22 03:22:00 UTC" \
  --target-db-url "postgresql+asyncpg://new-host:5432/mcp_fabric"

# Validate restored state
fabric-admin restore validate \
  --db-url "postgresql+asyncpg://new-host:5432/mcp_fabric"
# Checks:
#   - Server count matches expected
#   - All server endpoints are reachable (health check)
#   - Capability mappings resolve (no orphaned mappings)
#   - Agent tokens are valid (hash check)
#   - Capability packs have valid assignments
#   - Audit event count is within expected range
#   - No foreign key violations

# Dry run (test restore without applying)
fabric-admin restore latest --dry-run
```

### 16.4 Restore Procedure (Operational Runbook)

```bash
# 1. Detect failure
#    Alert: Fabric API returns 500s, PostgreSQL is unreachable
#    Metrics: DB connection errors spike in Prometheus

# 2. Provision fresh PostgreSQL
createdb mcp_fabric_restored

# 3. Run restore
fabric-admin restore latest \
  --target-db-url "postgresql+asyncpg://new-pg:5432/mcp_fabric_restored"

# 4. Validate
fabric-admin restore validate \
  --db-url "postgresql+asyncpg://new-pg:5432/mcp_fabric_restored"
# Expected output: "14/14 checks passed. State valid."

# 5. Point Fabric to restored DB
export DATABASE_URL="postgresql+asyncpg://new-pg:5432/mcp_fabric_restored"
# Restart Fabric API instances

# 6. Health check
curl http://fabric:8000/v1/health
# Expected: {"status": "healthy", "database": "connected", "redis": "connected"}

# 7. Verify agent functionality
curl -X POST http://fabric:8000/v1/capability/request \
  -H "Authorization: Bearer <test-token>" \
  -d '{"capability": "code:search", "params": {"query": "test"}}'
# Expected: 200 with results

# 8. Document incident
#   - Downtime: start → end timestamps
#   - Data loss window: between last WAL archive and failure
#   - Affected agent classes / servers
#   - Root cause of PostgreSQL failure
#   - Preventive actions
```

### 16.5 Redis Recovery

Redis state is ephemeral and rebuilt automatically:
- **Agent sessions:** TTL-based, expire naturally. Agents re-authenticate.
- **Rate limit counters:** Reset on Redis restart. Acceptable for recovery.
- **Server health state:** Rebuilt by next Celery health check (within 30 seconds).
- **Celery broker state:** In-flight tasks may be lost. Idempotent task design handles retry.

No Redis backup needed. All durable state is in PostgreSQL.

---

## 17. Fabric Version Upgrade — Zero Downtime (Journey 25)

### 17.1 Backward Compatibility Guarantee

Fabric API follows these compatibility rules across minor versions:

| Change Type | Allowed in minor? | Example |
|---|---|---|
| Add new endpoint | Yes | POST /v1/capability/batch added in v0.2.0 |
| Add optional field to request | Yes | New `routing_hint` field in capability request |
| Add field to response | Yes | New `deprecated` field in capability surface |
| Change field type | No (major only) | String → integer |
| Remove endpoint | No (major only) | Deprecate first, remove in next major |
| Remove field from response | No (major only) | Must be opt-in or major version |
| Change error format | No (major only) | Error structure is a contract |

### 17.2 API Version Header Support

Old agents (pre-upgrade) continue to work because:
1. They send `Accept: application/vnd.fabric.v1+json` (or no version header → defaults to latest)
2. New API endpoints are additive — old endpoints are unchanged
3. Response format is backward-compatible

```python
# api/dependencies.py — version middleware
async def get_api_version(request: Request) -> str:
    accept = request.headers.get("Accept", "")
    match = re.search(r"application/vnd\.fabric\.(v\d+)\+json", accept)
    if match:
        return match.group(1)
    # Default to latest
    return "v1"
```

### 17.3 Database Migration Strategy

```python
# Migrations follow these rules:
# 1. Additive migrations only (new tables, new columns with defaults)
# 2. No destructive migrations (DROP TABLE, DROP COLUMN)
# 3. Destructive changes are deferred to next major version
# 4. Migrations are backward-compatible: old API instances work with new schema

# Example: adding capability_packs table (v0.1.0 → v0.2.0)
# Migration: CREATE TABLE capability_packs (...)
# Old API instances: ignore the new table (don't query it)
# New API instances: query it for pack features
# Both can run simultaneously during blue-green deployment
```

### 17.4 Blue-Green Deployment Procedure

```
Before upgrade:
┌──────────────┐     ┌──────────────┐
│ API Instance A│     │ API Instance B│
│ (v0.1.0)     │     │ (v0.1.0)     │
└──────┬───────┘     └──────┬───────┘
       │                    │
       └────────┬───────────┘
                │
        ┌───────▼───────┐
        │ Load Balancer │  ← agents connect here
        └───────────────┘

Step 1: Take Instance B out of rotation
        ┌──────────────┐     ┌──────────────┐
        │ API Instance A│     │ API Instance B│  ← out of rotation
        │ (v0.1.0)     │     │ (v0.1.0)     │
        └──────┬───────┘     └──────────────┘
               │
        ┌──────▼──────┐
        │ Load Balancer│  ← all traffic to A
        └─────────────┘

Step 2: Upgrade Instance B
        ┌──────────────┐     ┌──────────────┐
        │ API Instance A│     │ API Instance B│
        │ (v0.1.0)     │     │ (v0.2.0)     │  ← upgraded
        └──────┬───────┘     └──────────────┘
               │
        ┌──────▼──────┐
        │ Load Balancer│
        └─────────────┘

Step 3: Run migrations on Instance B
        alembic upgrade head
        → Creates new tables, adds columns
        → v0.1.0 Instance A continues unaffected

Step 4: Validate Instance B
        Health check: GET /v1/health → 200
        Smoke test: capability request → 200
        New endpoints: POST /v1/capability/batch → 200

Step 5: Put B back, take A out
        ┌──────────────┐     ┌──────────────┐
        │ API Instance A│     │ API Instance B│
        │ (v0.1.0)     │     │ (v0.2.0)     │  ← now serving
        └──────────────┘     └──────┬───────┘
                                    │
                            ┌───────▼──────┐
                            │ Load Balancer│
                            └──────────────┘

Step 6: Upgrade Instance A (same as Step 2-4)
        Both instances now v0.2.0

Result: Zero dropped requests. Zero 5xx errors during deployment.
```

### 17.5 Celery Worker Upgrade

Celery workers follow a **drain-then-upgrade** pattern:

```bash
# 1. Gracefully drain old workers (stop accepting new tasks, finish current)
celery -A api.tasks control shutdown destination=worker@old-host

# 2. Start new workers with updated code
celery -A api.tasks worker --loglevel=info --hostname=worker@new-host

# 3. Verify new workers are processing tasks
celery -A api.tasks inspect active
```

### 17.6 Rollback Procedure

If validation fails at Step 4:

```bash
# 1. Take upgraded instance out of rotation immediately
# 2. Revert database migrations
alembic downgrade -1

# 3. Redeploy previous version
docker-compose up api  # with v0.1.0 image tag

# 4. Validate health
curl http://fabric:8000/v1/health

# 5. Put back in rotation
# Total rollback time: < 2 minutes
```

---

## 18. Development Setup

```bash
# Prerequisites: Python 3.12+, Poetry, Docker (optional for PostgreSQL mode)

# Clone
git clone https://github.com/deghosal-2026/mcp-fabric.git
cd mcp-fabric

# Install dependencies (Poetry creates a virtualenv automatically)
poetry install

# SQLite mode (zero Docker):
#   Just run the app — SQLite is the default
poetry run uvicorn api.main:app --reload
#   API: http://localhost:8000
#   Docs: http://localhost:8000/docs

# PostgreSQL mode (requires Docker):
docker-compose up -d postgres redis opa
poetry run alembic upgrade head
poetry run uvicorn api.main:app --reload

# Full stack mode (everything in Docker):
docker-compose up
# Includes: API, UI, PostgreSQL, Redis, OPA, Celery worker, Celery beat

# Run tests
poetry run pytest tests/ -v

# Run tests with coverage
poetry run pytest tests/ -v --cov=api --cov-report=term-missing

# Lint
poetry run ruff check api/ tests/

# Format
poetry run ruff format api/ tests/

# Database: create migration after model changes
poetry run alembic revision --autogenerate -m "description"

# Database: apply migrations
poetry run alembic upgrade head

# Start Celery worker (separate terminal)
poetry run celery -A api.tasks worker --loglevel=info

# Start Celery beat (separate terminal — for scheduled tasks)
poetry run celery -A api.tasks beat --loglevel=info

# Start OPA (separate terminal — or use docker-compose)
opa run --server --addr localhost:8181 policies/
```
