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

### v0.1.0 — Core Platform (Weeks 1-6)

**Goal:** A complete routing + governance platform. Agent routes a capability request through Fabric, gets a correct policy-checked audited response, and platform team has full lifecycle management of servers and capabilities.

**Deliverables:**

| # | Feature | Journey | Acceptance |
|---|---|---|---|
| 1 | Server registry — register, inspect, list, get, decommission | 1, 11 | Server registered with auto-inspected tools. Phased decommission works. |
| 2 | Schema diff on re-inspect | 10 | Breaking changes flagged, diff visible in UI. History stored in tool_versions. |
| 3 | Capability catalog — create, map, list, aliases, deprecate | 12, 27 | Capability created, tool mapped, alias resolved. Deprecation returns 410 with guidance. |
| 4 | Conflict detection | 9 | Two servers mapping to same capability → flag in UI. Resolution deferred to v0.2.0. |
| 5 | Routing engine — single + batch capability request | 2, 23 | Request routed → policy checked → response normalized. Batch handles parallel execution. |
| 6 | Fallback chain | 6 | Primary server timeout → fallback server → degradation logged → alert triggered. |
| 7 | OPA policy engine — allow/deny/approval-gated | 2, 7 | Rego policies evaluate. Denied requests return 403. Gated requests create approval. |
| 8 | Approval-gated workflow | 7 | Agent requests gated capability → approval created → human reviews → approve/deny → audit. |
| 9 | Agent auth — token create, rotate, revoke, connect, capability surface | 5, 21, 29 | Token lifecycle complete. Agent connects → receives scoped capability surface. |
| 10 | Admin auth — login, MFA, session, logout | 26, 29 | Admin logs in with password+MFA → JWT session → role-based UI access. |
| 11 | Capability discovery — full schema + change webhooks | 22 | Agent queries /capabilities/available → gets schemas + deprecation notices. |
| 12 | Error handling — 12 structured error types | 13 | Every error returns code + message + details + request_id. |
| 13 | Audit pipeline — log, query, export | 4, 18 | All events captured. Queryable by type/actor/date. Export to JSON/CSV. |
| 14 | Admin UI — dashboard, servers, capabilities, audit, approvals, agent classes, alerts, users, trust posture | 1, 4, 8, 17 | All 12 pages functional with loading/empty/error/populated states. |
| 15 | Health endpoints — /health, /health/ready, /health/live | — | Readiness/liveness probes. Graceful shutdown. |
| 16 | Telemetry — Prometheus metrics, OpenTelemetry traces, structlog | 28 | All 15 metric families exported. Request lifecycle traced. Structured JSON logs. |
| 17 | Celery workers — health checks, alerts, approval notifications, audit export, retention cleanup | 6, 7, 18 | Tasks execute, retry, and report completion. |
| 18 | SQLite (local dev) + PostgreSQL (production) | 8 | Zero-config SQLite. Identical behavior with PostgreSQL via config swap. |
| 19 | Docker Compose + Poetry + Makefile + CI/CD | 8, 22 | `docker-compose up` works. `make test` passes. GitHub Actions CI green. |
| 20 | Test suite — 75% unit, 20% integration, 5% E2E. OPA policy tests. | — | All P0+P1 scenarios pass. Coverage >80%. |
| 21 | Capability packs — create, assign, edit, clone | 3 | Pack created → capabilities selected → assigned to class → agent sees scoped surface. |
| 22 | Basic routing rules — priority-based ordering | 9 | ORDER BY priority on capability mappings. Explicit "prefer Server A" without conditions. |
| 23 | Multi-team namespaces — row-level filtering, team-scoped admin roles | 20 | TenantMiddleware enforces namespace on all queries. Editor role scoped to team. |
| 24 | Admin user management — invite, roles, MFA, deactivate | 26 | Full admin lifecycle: invite → setup → login+MFA → session → deactivate → revoke. |

### v0.2.0 — Hardening (Weeks 7-12)

**Goal:** Production readiness — safe change management, migration tooling, disaster recovery, and validated performance.

| # | Feature | Journey | Acceptance |
|---|---|---|---|
| 1 | Policy sandbox — shadow evaluation | 19 | New trust rule evaluated against real traffic for 48h → side-by-side results → activate or discard. |
| 2 | Conditional routing rules | 9 | Rules with parameter-based conditions (e.g., "when `file_pattern` present, route to Server A"). |
| 3 | Incremental migration — dual-mode routing | 15 | Agent config specifies per-capability mode (fabric/direct). Migration status API. Validation checklist. |
| 4 | Fabric backup/restore — CLI tooling | 24 | `fabric-admin backup` + `fabric-admin restore` with PITR support. Validate after restore. |
| 5 | Fabric version upgrade — blue-green | 25 | Zero-downtime upgrade. API backward compatibility verified. Rollback tested. |
| 6 | Performance benchmark suite | — | Load tests validate v0.1.0 targets. Chaos tests for DB/Redis/OPA failures. Bottlenecks resolved. |
| 7 | Reference MCP server integrations | — | Tested with 5+ popular OSS MCP servers. Integration guide published. |

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

## 18. API Pagination, Filtering, and Sorting

### 18.1 Pagination Strategy

All list endpoints use **cursor-based pagination** for large datasets (audit, servers) and **offset-based** for small datasets (capabilities, agent classes).

```json
// Request
GET /v1/audit?event_type=capability_request&cursor=eyJpZCI6IjEyMyJ9&per_page=50

// Response
{
    "events": [...],
    "pagination": {
        "next_cursor": "eyJpZCI6IjE3MyJ9",
        "has_more": true,
        "per_page": 50,
        "total": 14203
    }
}
```

| Endpoint | Strategy | Default per_page | Max per_page |
|---|---|---|---|
| `GET /servers` | Cursor (by created_at) | 50 | 200 |
| `GET /capabilities` | Offset | 100 | 500 |
| `GET /audit` | Cursor (by created_at DESC) | 50 | 200 |
| `GET /approvals` | Cursor (by requested_at) | 50 | 100 |
| `GET /alerts` | Cursor (by fired_at) | 50 | 100 |
| `GET /agent-classes` | Offset | 50 | 100 |
| `GET /packs` | Offset | 50 | 100 |
| `GET /admin/users` | Offset | 50 | 100 |

### 18.2 Filtering

```python
# Common filter pattern for all list endpoints
GET /v1/servers?team_namespace=team:platform&trust_level=trusted&health_status=healthy&q=search
GET /v1/audit?event_type=capability_request&actor_type=agent&actor_id=dev-agent-01&from=2026-07-01&to=2026-07-31
GET /v1/capabilities?domain=code&status=active&q=search

# Filter parameters are validated against allowed values
# Unknown filter params return 400: {"error": "invalid_filter", "parameter": "color"}
```

### 18.3 Sorting

```python
# Sort by any sortable field, ascending or descending
GET /v1/servers?sort=created_at&order=desc
GET /v1/audit?sort=created_at&order=asc
GET /v1/capabilities?sort=name&order=asc

# Allowed sort fields per endpoint:
# /servers: name, created_at, health_status, trust_level
# /audit: created_at (only — immutable log)
# /capabilities: name, domain, created_at
# /approvals: requested_at, status
```

### 18.4 OpenAPI Documentation

FastAPI auto-generates OpenAPI 3.1 spec at:

```
GET /docs      — Swagger UI (interactive)
GET /redoc     — ReDoc (documentation)
GET /openapi.json — Raw OpenAPI spec
```

The OpenAPI spec includes all request/response schemas, validation rules, and examples. It is the authoritative API reference.

### 18.5 Webhook Delivery Specification

```python
# Webhook registration (from Journey 22)
POST /v1/agents/{agent_id}/webhooks
Body: {
    "url": "https://igor.internal/fabric-events",
    "events": ["capability_added", "capability_deprecated", "capability_schema_changed"]
}
Response 201: {
    "id": "uuid",
    "webhook_secret": "whsec_xxxx",   # HMAC-SHA256 signing secret
    "url": "https://...",
    "events": [...]
}
```

**Delivery:**
- Method: `POST` to registered URL
- Header: `Fabric-Webhook-Signature: sha256=<hmac>`
- Body: JSON event payload
- Timeout: 10 seconds
- Retry: 3 attempts with exponential backoff (1s, 5s, 25s)
- Failure: After 3 failed attempts, webhook is marked `degraded`
- Reactivation: Manual or automatic after 1 hour of successful deliveries

**Signature verification (agent side):**
```python
import hmac, hashlib

def verify_webhook(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## 19. Entity Relationship Diagram

```
┌───────────────────┐       ┌───────────────────┐
│   mcp_servers     │       │   capabilities    │
│───────────────────│       │───────────────────│
│ id (PK)           │       │ id (PK)           │
│ name              │       │ name (UQ)         │
│ endpoint          │       │ domain            │
│ owner_team        │       │ norm_input_schema │
│ labels (JSONB)    │       │ norm_output_schema│
│ trust_level       │       │ description       │
│ health_status     │       │ status            │
│ team_namespace    │       │ deprecated_at     │
│ decommissioned_at │       │ grace_period_days │
└──────┬────────────┘       └────────┬──────────┘
       │                             │
       │ 1:N                         │ 1:N
       ▼                             ▼
┌───────────────────┐       ┌──────────────────────────────────────┐
│   server_tools    │       │        capability_mappings           │
│───────────────────│       │──────────────────────────────────────│
│ id (PK)           │       │ id (PK)                              │
│ server_id (FK)────┼──┐    │ capability_id (FK)────────────────────┼──┐
│ tool_name         │  │    │ server_id (FK)──────────────────────┐│  │
│ input_schema(JSONB)│  │    │ tool_name                          ││  │
│ output_schema(JSONB)│  │    │ input_mapping (JSONB)             ││  │
└───────────────────┘  │    │ output_mapping (JSONB)             ││  │
                       │    │ is_primary                         ││  │
┌───────────────────┐  │    │ routing_weight                     ││  │
│  tool_versions    │  │    └────────────────────────────────────┘│  │
│───────────────────│  │                                          │  │
│ id (PK)           │  │    ┌──────────────────────────────────┐  │  │
│ server_id (FK)────┼──┘    │        routing_rules             │  │  │
│ tool_name         │       │──────────────────────────────────│  │  │
│ input_schema(JSONB)│      │ id (PK)                          │  │  │
│ output_schema(JSONB)│     │ capability_id (FK)───────────────┼──┘  │
│ is_breaking       │       │ server_id (FK)───────────────────┼─────┘
│ detected_at       │       │ priority                         │
└───────────────────┘       │ condition (JSONB)                │
                            └──────────────────────────────────┘

┌───────────────────┐       ┌──────────────────────────────────────┐
│  agent_classes    │       │         trust_assignments            │
│───────────────────│       │──────────────────────────────────────│
│ id (PK)           │◄──────│ agent_class_id (FK)                  │
│ name (UQ)         │       │ server_id (FK)──────────────────────┐│
│ team_namespace    │       │ trust_level                         ││
└────────┬──────────┘       │ tool_scope (JSONB)                  ││
         │                  └─────────────────────────────────────┘│
         │ 1:N                                                     │
         ▼                                                         │
┌───────────────────┐                                              │
│ agent_identities  │                                              │
│───────────────────│                                              │
│ id (PK)           │                                              │
│ agent_class_id(FK)│                                              │
│ token_hash        │       ┌──────────────────────────────────┐   │
│ token_prefix      │       │       approval_requests          │   │
│ status            │       │──────────────────────────────────│   │
│ rate_limit_per_min│       │ id (PK)                          │   │
│ expires_at        │       │ agent_identity_id (FK)───────────┼───┘
└───────────────────┘       │ capability_id (FK)               │
                            │ server_id (FK)───────────────────┼───┐
┌───────────────────┐       │ request_params (JSONB)           │   │
│ capability_packs  │       │ status                           │   │
│───────────────────│       │ approver_id (FK)                 │◄──┼──┐
│ id (PK)           │       │ requested_at                     │   │  │
│ name (UQ)         │       │ resolved_at                      │   │  │
│ team_namespace    │       └──────────────────────────────────┘   │  │
└────────┬──────────┘                                              │  │
         │                                                         │  │
         │ N:M (via pack_assignments)                               │  │
         ▼                                                         │  │
┌──────────────────────────────────────┐                            │  │
│          pack_assignments            │                            │  │
│──────────────────────────────────────│                            │  │
│ pack_id (FK) ────────────────────────┼── capability_packs.id     │  │
│ capability_id (FK) ──────────────────┼── capabilities.id         │  │
└──────────────────────────────────────┘                            │  │
                                                                    │  │
┌──────────────────────────────────────┐                            │  │
│        agent_class_packs             │                            │  │
│──────────────────────────────────────│                            │  │
│ agent_class_id (FK) ─────────────────┼── agent_classes.id        │  │
│ pack_id (FK) ────────────────────────┼── capability_packs.id     │  │
└──────────────────────────────────────┘                            │  │
                                                                    │  │
┌───────────────────┐       ┌──────────────────────────────────┐   │  │
│   admin_users     │       │          audit_events            │   │  │
│───────────────────│       │──────────────────────────────────│   │  │
│ id (PK)───────────┼──┐    │ id (PK)                          │   │  │
│ username (UQ)     │  │    │ event_type                       │   │  │
│ email (UQ)        │  │    │ actor_type                       │   │  │
│ password_hash     │  │    │ actor_id                         │   │  │
│ role              │  │    │ target_type                      │   │  │
│ team_namespace    │  │    │ target_id                        │   │  │
│ mfa_enabled       │  │    │ details (JSONB)                  │   │  │
│ status            │  │    │ created_at                       │   │  │
└───────────────────┘  │    └──────────────────────────────────┘   │  │
                       │                                            │  │
┌───────────────────┐  │    ┌──────────────────────────────────┐    │  │
│  alert_rules      │  │    │         alert_events             │    │  │
│───────────────────│  │    │──────────────────────────────────│    │  │
│ id (PK)           │  │    │ id (PK)                          │    │  │
│ name              │  │    │ rule_id (FK)─────────────────────┼────┼──┘
│ alert_type        │  │    │ message                          │    │
│ condition (JSONB) │  │    │ details (JSONB)                  │    │
│ channels (JSONB)  │  │    │ fired_at                         │    │
│ enabled           │  │    │ acknowledged_at                   │    │
└───────────────────┘  │    │ acknowledged_by (FK)──────────────┼────┘
                       │    └──────────────────────────────────┘
┌───────────────────┐  │
│capability_aliases │  │
│───────────────────│  │
│ id (PK)           │  │
│ capability_id(FK)─┼──┼── capabilities.id
│ alias (UQ)        │  │
└───────────────────┘  │
                       │
┌───────────────────┐  │
│ opa_policy_versions│  │
│───────────────────│  │
│ id (PK)           │  │
│ version           │  │
│ bundle_hash       │  │
│ deployed_by (FK)──┼──┘
│ rego_content      │
└───────────────────┘
```

### 19.1 Indexing Strategy

```sql
-- Hot-path indexes (every capability request hits these)
CREATE INDEX idx_tools_server ON server_tools(server_id);
CREATE INDEX idx_mappings_capability ON capability_mappings(capability_id);
CREATE INDEX idx_mappings_server ON capability_mappings(server_id);
CREATE INDEX idx_trust_class ON trust_assignments(agent_class_id);
CREATE UNIQUE INDEX idx_trust_unique ON trust_assignments(agent_class_id, server_id);
CREATE INDEX idx_identities_token ON agent_identities(token_hash);

-- Audit query indexes
CREATE INDEX idx_audit_type ON audit_events(event_type);
CREATE INDEX idx_audit_actor ON audit_events(actor_type, actor_id);
CREATE INDEX idx_audit_time ON audit_events(created_at DESC);
CREATE INDEX idx_audit_type_time ON audit_events(event_type, created_at DESC);

-- Admin query indexes
CREATE INDEX idx_servers_team ON mcp_servers(team_namespace);
CREATE INDEX idx_servers_trust ON mcp_servers(trust_level);
CREATE INDEX idx_servers_health ON mcp_servers(health_status);
CREATE INDEX idx_capabilities_domain ON capabilities(domain);
CREATE INDEX idx_capabilities_status ON capabilities(status);
CREATE INDEX idx_capabilities_name ON capabilities(name);

-- Approval indexes
CREATE INDEX idx_approvals_status ON approval_requests(status);
CREATE INDEX idx_approvals_agent ON approval_requests(agent_identity_id);

-- Lookup indexes
CREATE INDEX idx_aliases_alias ON capability_aliases(alias);
CREATE INDEX idx_aliases_capability ON capability_aliases(capability_id);

-- Alert indexes
CREATE INDEX idx_alerts_fired ON alert_events(fired_at DESC);
CREATE INDEX idx_alerts_rule ON alert_events(rule_id);

-- Agent indexes
CREATE INDEX idx_identities_class ON agent_identities(agent_class_id);
CREATE INDEX idx_identities_status ON agent_identities(status);
```

### 19.2 Migration Safety Rules

```
1. All migrations MUST be additive (CREATE TABLE, ALTER TABLE ADD COLUMN).
2. New columns MUST have DEFAULT values or be NULLABLE.
3. No DROP TABLE, DROP COLUMN, or RENAME COLUMN in minor versions.
4. Destructive changes are deferred to next MAJOR version (v2.0.0).
5. Each migration is tested against SQLite AND PostgreSQL.
6. Migrations are backward-compatible: old API instances work with new schema.
7. Migration rollback is tested before deployment (alembic downgrade -1).
8. Long-running migrations (>5s) must use batched operations with lock timeouts.
```

---

## 20. Operational Runbook

### 20.1 Graceful Shutdown

```python
# api/main.py
import signal
import asyncio

async def shutdown():
    """Gracefully drain in-flight requests before shutting down."""
    # 1. Stop accepting new requests (health check reports "shutting_down")
    app.state.readiness = "shutting_down"

    # 2. Wait for in-flight requests to complete (max 30s grace period)
    await asyncio.sleep(5)  # give existing requests time to finish

    # 3. Close database connections
    await db.dispose()

    # 4. Close Redis connections
    await redis.close()

    # 5. Close MCP client sessions
    await mcp_client.close()

    # 6. Flush telemetry
    # (OpenTelemetry SDK flushes on shutdown)

# Register signal handlers
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

# Kubernetes: terminationGracePeriodSeconds: 35

# Sequence:
# 1. SIGTERM received
# 2. /health reports "shutting_down" → load balancer removes pod
# 3. 5s grace for LB to drain
# 4. Wait for in-flight requests (up to 25s)
# 5. Close connections
# 6. Process exits with code 0
```

### 20.2 Health Probes

```
GET /health
Response 200:
{
    "status": "healthy",         // healthy | degraded | shutting_down
    "version": "0.1.0",
    "uptime_seconds": 123456,
    "checks": {
        "database": "connected", // connected | disconnected
        "redis": "connected",
        "opa": "connected"
    }
}

GET /health/ready                  // Readiness probe
Response 200: {"status": "ready"}  // ready | shutting_down
# Kubernetes: readinessProbe → controls service routing
# Returns 503 when shutting down (LB removes pod)

GET /health/live                   // Liveness probe
Response 200: {"status": "alive"}
# Kubernetes: livenessProbe → controls pod restart
# Returns 200 as long as process is running (doesn't check dependencies)
# Only returns 500 if process is deadlocked

Kubernetes probe configuration:
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3

livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 10
  failureThreshold: 3
```

### 20.3 Logging Strategy

```python
# structlog configuration
# Levels:
#   DEBUG — Full request/response bodies, SQL queries, OPA decision details
#   INFO  — Request method + path + status + latency, server registrations, policy changes
#   WARN  — Degraded servers, fallback events, rate limit hits, token near expiry
#   ERROR — Server failures, DB/Redis connection errors, OPA unreachable, 5xx responses

# Production log format (JSON):
{
    "timestamp": "2026-07-22T14:30:00.123Z",
    "level": "info",
    "event": "capability_request",
    "request_id": "req_abc123",
    "agent_id": "dev-agent-01",
    "agent_class": "agent:developer",
    "capability": "code:search",
    "server": "code-search",
    "latency_ms": 320,
    "status": 200,
    "routing_reason": "primary server, best match"
}

# What is NOT logged:
# - Agent tokens (only token_hash prefix)
# - Capability request parameter values (sanitized: {"query": "***"})
# - MCP server response bodies (metadata only)
# - Admin passwords (never logged, even in DEBUG)
```

---

## 21. Metrics and Tracing Definitions

### 21.1 Prometheus Metrics

```python
# api/telemetry/metrics.py

from prometheus_client import Counter, Histogram, Gauge, Info

# Request metrics
fabric_requests_total = Counter(
    "fabric_requests_total",
    "Total capability requests",
    ["agent_class", "capability", "status"]  # status: success, denied, error, fallback
)

fabric_request_duration_seconds = Histogram(
    "fabric_request_duration_seconds",
    "Capability request duration (total: resolve + policy + route + server_call + normalize)",
    ["agent_class", "capability", "server"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

fabric_routing_overhead_seconds = Histogram(
    "fabric_routing_overhead_seconds",
    "Fabric-internal routing time (resolve + policy + select — excluding server call)",
    ["agent_class", "capability"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25]
)

# Server health metrics
fabric_server_health = Gauge(
    "fabric_server_health",
    "MCP server health status",
    ["server_name", "server_id"]
)  # 1 = healthy, 0.5 = degraded, 0 = unhealthy

fabric_server_tool_count = Gauge(
    "fabric_server_tool_count",
    "Number of tools exposed per server",
    ["server_name"]
)

# Policy metrics
fabric_policy_decisions_total = Counter(
    "fabric_policy_decisions_total",
    "Total OPA policy evaluations",
    ["agent_class", "decision"]  # decision: allow, deny, approval_required
)

fabric_policy_evaluation_duration = Histogram(
    "fabric_policy_evaluation_duration_seconds",
    "OPA policy evaluation duration",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05]
)

# Approval metrics
fabric_approvals_pending = Gauge(
    "fabric_approvals_pending",
    "Number of pending approval requests"
)

fabric_approval_duration_minutes = Histogram(
    "fabric_approval_duration_minutes",
    "Time from approval request to resolution",
    buckets=[1, 5, 15, 30, 60, 120, 240, 480]
)

# Audit metrics
fabric_audit_events_total = Counter(
    "fabric_audit_events_total",
    "Total audit events written",
    ["event_type"]
)

# Infrastructure metrics
fabric_db_connections = Gauge(
    "fabric_db_connections",
    "Active database connections"
)

fabric_redis_connections = Gauge(
    "fabric_redis_connections",
    "Active Redis connections"
)

fabric_celery_tasks_total = Counter(
    "fabric_celery_tasks_total",
    "Total Celery tasks executed",
    ["task_type", "status"]  # status: success, failure, retry
)

# API info
fabric_info = Info("fabric", "Fabric instance metadata")
fabric_info.info({
    "version": "0.1.0",
    "environment": "production"
})
```

### 21.2 OpenTelemetry Spans

```
Request Trace: POST /v1/capability/request
│
├── Span: "capability_request" (root)
│   Attributes: agent_id, agent_class, capability, params_hash
│
├── Span: "resolve_capability"
│   Attributes: capability_name, resolved_to, match_type (exact/alias)
│   Events: candidate_count=3
│
├── Span: "evaluate_policy"
│   Attributes: agent_class, server_id, trust_level
│   Events: opa_decision=allow, opa_duration_ms=12
│
├── Span: "select_server"
│   Attributes: candidates_evaluated=3, selected_server, routing_reason
│   Events: ranking_scores=[0.95, 0.80, 0.60]
│
├── Span: "call_mcp_server"
│   Attributes: server_name, server_endpoint, tool_name
│   Events: timeout=5000ms, retry_count=0
│   │
│   ├── Span: "mcp_tools_call" (external call via mcp SDK)
│   │   Attributes: http.method=POST, http.url=..., http.status_code=200
│   │
│   └── (if fallback) Span: "fallback_call_mcp_server"
│       Events: primary_failed_reason=timeout, fallback_server=git-history
│
├── Span: "normalize_response"
│   Attributes: output_mapping_applied=true, schema_match=true
│
└── Span: "write_audit_event"
    Attributes: event_type=capability_request, event_id=uuid
```

### 21.3 Grafana Dashboard (Outline)

| Panel | Metric | Type |
|---|---|---|
| Request rate | `rate(fabric_requests_total[5m])` | Graph (timeseries) |
| Request latency (p50/p95/p99) | `histogram_quantile(0.95, fabric_request_duration_seconds)` | Graph |
| Routing overhead | `histogram_quantile(0.95, fabric_routing_overhead_seconds)` | Graph |
| Requests by agent class | `sum(fabric_requests_total) by (agent_class)` | Bar chart |
| Requests by capability | `sum(fabric_requests_total) by (capability)` | Bar chart |
| Error rate | `rate(fabric_requests_total{status="error"}[5m])` | Graph |
| Denial rate | `rate(fabric_requests_total{status="denied"}[5m])` | Graph |
| Fallback rate | `rate(fabric_requests_total{status="fallback"}[5m])` | Graph |
| Server health | `fabric_server_health` | Status grid |
| Pending approvals | `fabric_approvals_pending` | Stat |
| Approval resolution time | `histogram_quantile(0.95, fabric_approval_duration_minutes)` | Graph |
| OPA evaluation latency | `histogram_quantile(0.95, fabric_policy_evaluation_duration)` | Graph |
| DB connections | `fabric_db_connections` | Graph |
| Celery task status | `rate(fabric_celery_tasks_total[5m])` | Graph |

---

## 22. CI/CD Pipeline (GitHub Actions)

### 22.1 Pipeline Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ruff
      - run: ruff check api/ tests/
      - run: ruff format --check api/ tests/

  test-sqlite:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install poetry && poetry install
      - run: poetry run pytest tests/ -v --cov=api --cov-report=xml
        env:
          DATABASE_URL: sqlite+aiosqlite:///:memory:
          REDIS_URL: redis://localhost:6379/0
          ENVIRONMENT: testing
      - uses: codecov/codecov-action@v4
        with: { file: ./coverage.xml }

  test-postgres:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_USER: fabric, POSTGRES_PASSWORD: fabric, POSTGRES_DB: mcp_fabric }
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
      opa:
        image: openpolicyagent/opa:latest
        ports: ["8181:8181"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install poetry && poetry install
      - run: poetry run alembic upgrade head
      - run: poetry run pytest tests/ -v -m "integration"
        env:
          DATABASE_URL: postgresql+asyncpg://fabric:fabric@localhost:5432/mcp_fabric
          REDIS_URL: redis://localhost:6379/0
          OPA_URL: http://localhost:8181
          ENVIRONMENT: testing

  opa-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: open-policy-agent/setup-opa@v2
        with: { version: "0.68.0" }
      - run: opa test policies/ -v

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install poetry && poetry install
      - run: poetry run mypy api/

  ui-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd ui && npm ci && npm run lint && npm run typecheck
```

### 22.2 Release Pipeline

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags: ["v*"]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
      - uses: docker/build-push-action@v6
        with: { push: true, tags: ghcr.io/deghosal-2026/mcp-fabric:${{ github.ref_name }}, ghcr.io/deghosal-2026/mcp-fabric:latest }
      - run: poetry build && poetry publish
```

### 22.3 Required GitHub Secrets

| Secret | Purpose |
|---|---|
| `GITHUB_TOKEN` | Auto-provided — Docker push, release creation |
| `PYPI_TOKEN` | Poetry publish to PyPI |
| `CODECOV_TOKEN` | Coverage upload (optional for public repo) |

---

## 23. Performance Targets

### 23.1 Latency SLAs

| Operation | Target (p95) | Budget |
|---|---|---|
| Capability request (total) | < 500ms | Server call: ~450ms, Fabric overhead: ~50ms |
| Fabric routing overhead | < 50ms | Resolve: 10ms, policy: 15ms, select: 5ms, normalize: 10ms, audit: 10ms |
| OPA policy evaluation | < 25ms | Single Rego evaluation, cached in OPA |
| Server registration + inspect | < 5s | Includes MCP server /tools/list call |
| Capability listing (100 items) | < 100ms | With JSONB schema fields |
| Audit query (50 events) | < 200ms | With filtered Cursor pagination |
| Batch request (3 capabilities) | < max(server_calls) + 50ms | Parallel execution |
| Agent connect + capability surface | < 50ms | Token lookup + class resolution |
| Health check | < 10ms | DB ping + Redis ping |

### 23.2 Throughput Targets

| Metric | Target (single instance) |
|---|---|
| Concurrent capability requests | 500 |
| Capability requests/second | 1000 |
| Server registrations/minute | 10 |
| Audit events written/second | 2000 |
| Batch requests (3 capabilities) / second | 300 |

### 23.3 Resource Limits

| Component | CPU (request/limit) | Memory (request/limit) |
|---|---|---|
| Fabric API | 500m / 2000m | 512Mi / 2Gi |
| Celery worker | 250m / 1000m | 256Mi / 1Gi |
| Celery beat | 100m / 250m | 128Mi / 256Mi |
| PostgreSQL | 1000m / 4000m | 1Gi / 4Gi |
| Redis | 250m / 1000m | 256Mi / 2Gi |
| OPA | 100m / 500m | 128Mi / 512Mi |

---

## 24. Initial OPA Policy Bootstrap

### 24.1 Default Policies (shipped with v0.1.0)

```rego
# policies/fabric/policy.rego
package fabric.policy

# ─── Trust Level Hierarchy ───
trust_levels := {
    "trusted": 3,
    "restricted": 2,
    "approval-gated": 1,
    "unreviewed": 0
}

# ─── Agent Class Defaults ───
# These ship with Fabric. Teams customize per their needs.
class_min_trust := {
    "agent:admin": 3,              # Full access
    "agent:incident-responder": 2, # Requires restricted+
    "agent:deploy-monitor": 2,     # Requires restricted+
    "agent:code-reviewer": 1,      # Can use approval-gated
    "agent:developer": 1,          # Can use approval-gated
    "agent:new-hire": 0            # Unreviewed servers only (safe training)
}

# ─── Main Allow Rule ───
default allow := false

allow {
    agent_trust := class_min_trust[input.agent_class]
    server_trust := trust_levels[input.server_trust_level]
    server_trust >= agent_trust
}

# ─── Approval Required Rule ───
approval_required {
    input.server_trust_level == "approval-gated"
    input.agent_class != "agent:admin"  # Admins bypass approval
}

# ─── Cross-Team Access ───
# Default: agents can access servers in their own team namespace or global servers
# Teams can override this rule for cross-team sharing
default cross_team_allowed := false

cross_team_allowed {
    input.agent_namespace == input.server_namespace
}

cross_team_allowed {
    input.server_namespace == ""  # Global/non-scoped servers
}

# ─── Decision Output ───
result := {
    "allow": allow,
    "approval_required": approval_required,
    "cross_team": cross_team_allowed,
    "trust_level": input.server_trust_level,
    "agent_class": input.agent_class
}
```

### 24.2 Policy Test Suite (shipped with v0.1.0)

```rego
# policies/fabric/policy_test.rego
package fabric.policy

test_admin_always_allowed {
    allow with input as {
        "agent_class": "agent:admin",
        "server_trust_level": "trusted",
        "agent_namespace": "team:platform",
        "server_namespace": "team:platform"
    }
}

test_incident_responder_allowed_restricted {
    allow with input as {
        "agent_class": "agent:incident-responder",
        "server_trust_level": "restricted"
    }
}

test_incident_responder_denied_unreviewed {
    not allow with input as {
        "agent_class": "agent:incident-responder",
        "server_trust_level": "unreviewed"
    }
}

test_new_hire_denied_any_trusted {
    not allow with input as {
        "agent_class": "agent:new-hire",
        "server_trust_level": "trusted"
    }
}

test_new_hire_allowed_unreviewed {
    allow with input as {
        "agent_class": "agent:new-hire",
        "server_trust_level": "unreviewed"
    }
}

test_developer_approval_required_for_gated {
    approval_required with input as {
        "agent_class": "agent:developer",
        "server_trust_level": "approval-gated"
    }
}

test_admin_no_approval_required {
    not approval_required with input as {
        "agent_class": "agent:admin",
        "server_trust_level": "approval-gated"
    }
}

test_cross_team_denied_by_default {
    not cross_team_allowed with input as {
        "agent_namespace": "team:platform",
        "server_namespace": "team:security"
    }
}

test_same_team_allowed {
    cross_team_allowed with input as {
        "agent_namespace": "team:platform",
        "server_namespace": "team:platform"
    }
}

test_global_server_allowed {
    cross_team_allowed with input as {
        "agent_namespace": "team:platform",
        "server_namespace": ""
    }
}
```

---

## 25. Admin UI Component Specifications

### 25.1 Common Patterns

Every page component handles these states:

```typescript
type PageState<T> =
  | { status: "loading" }
  | { status: "error"; error: string; retry: () => void }
  | { status: "empty"; message: string; action?: { label: string; onClick: () => void } }
  | { status: "populated"; data: T };
```

### 25.2 Dashboard (`/`)

| Aspect | Detail |
|---|---|
| **Purpose** | At-a-glance platform health and key metrics |
| **API calls** | `GET /health`, `GET /servers?per_page=0` (count only), `GET /audit?per_page=0` (count only) |
| **Widgets** | Server count + health breakdown, recent audit events (last 10), pending approvals count, degraded servers list |
| **Empty state** | "Welcome to MCP Fabric. Register your first server to get started." with CTA button |
| **Error state** | "Unable to load dashboard." with retry button |
| **Refresh** | Auto-refresh every 30 seconds via TanStack Query `refetchInterval` |

### 25.3 Servers (`/servers`)

| Aspect | Detail |
|---|---|
| **Purpose** | Server inventory — register, inspect, decommission |
| **API calls** | `GET /servers` (list), `POST /servers` (register), `POST /servers/{id}/inspect`, `POST /servers/{id}/decommission` |
| **List view** | Table: name, endpoint (truncated), trust level (badge), health (icon), tool count, last inspected, actions |
| **Filters** | Team namespace dropdown, trust level multi-select, health status multi-select, search (name/endpoint) |
| **Empty state** | "No servers registered yet." with "Register Server" button |
| **Register flow** | Modal: name, endpoint URL, owner team, description, labels (tag input), team namespace. On submit: auto-inspect, show imported tools, navigate to detail |
| **Detail view** | Server metadata, tool table (name, input/output schema preview, expandable), trust assignments, routing rules, decommission timeline (if applicable) |
| **Inspect action** | Button → loading → show diff (added/removed/changed tools) with breaking change warnings |
| **Decommission action** | Modal: select phase + replacement server → confirm → show dependency report |

### 25.4 Capability Catalog (`/capabilities`)

| Aspect | Detail |
|---|---|
| **Purpose** | Browse, create, map, deprecate capabilities |
| **API calls** | `GET /capabilities`, `POST /capabilities`, `POST /capabilities/{id}/mappings`, `POST /capabilities/{id}/deprecate`, `POST /capabilities/{id}/aliases` |
| **List view** | Table: name, domain (badge), status (active/deprecated badge), mapped tools count, aliases |
| **Filters** | Domain dropdown, status (active/deprecated), search (name/alias) |
| **Empty state** | "No capabilities defined. Create your first capability to start mapping tools." |
| **Create flow** | Modal: name (with domain:action convention helper), domain, description, normalized input/output schema editor (JSON editor with validation) |
| **Detail view** | Capability metadata, mapped servers table (server name, tool name, mapping status, routing weight), aliases list, deprecation info (if deprecated) |
| **Map tool flow** | Modal: select server → select tool → configure input/output mapping → save |
| **Conflict warning** | Banner at top of detail: "2 servers claim this capability. Review routing." with link to conflict resolver |
| **Deprecate flow** | Modal: grace period days, migration guidance text → confirm |

### 25.5 Agent Classes (`/agent-classes`)

| Aspect | Detail |
|---|---|
| **Purpose** | Create and manage agent classes, trust assignments, identity tokens |
| **API calls** | `GET /agent-classes`, `POST /agent-classes`, `POST /agent-classes/{id}/trust` |
| **List view** | Table: name, team namespace, server trust count, agent count, packs count |
| **Detail view** | Class metadata, trust assignments table (server, trust level badge, tool scope), assigned packs, agent identities list (name, status, token prefix, rate limit, expires) |
| **Create token flow** | Modal: agent name, rate limit → generate → show token ONCE with copy button + warning: "Save this token. It will not be shown again." |
| **Revoke token** | Confirm dialog → token status changes to "revoked", all active sessions invalidated |
| **Rotate token** | Modal: grace period hours → generate new token → old token enters grace period |

### 25.6 Policy Editor (`/policies`)

| Aspect | Detail |
|---|---|
| **Purpose** | Manage OPA policies, test sandbox changes |
| **API calls** | `POST /admin/policies/bundle`, `POST /policy/sandbox`, `GET /policy/sandbox/{id}` |
| **Rego editor** | Code editor (textarea with syntax highlighting or Monaco editor), deploy button, last deployed version + timestamp |
| **Sandbox** | Create: select trust change (class + server + new trust level) → "Start Sandbox" → real-time or refreshable results (would_approve, would_deny, false_positives, sample decisions) → "Activate" or "Discard" |

### 25.7 Audit Log (`/audit`)

| Aspect | Detail |
|---|---|
| **Purpose** | Query, filter, export audit events |
| **API calls** | `GET /audit`, `POST /audit/export` |
| **List view** | Table: timestamp, event type (badge), actor, target, summary (first 100 chars of details), expandable row for full details JSON |
| **Filters** | Event type multi-select, actor type (agent/admin/system), actor ID search, date range (date picker), capability filter |
| **Empty state** | "No audit events match your filters." |
| **Export** | Button → modal: select event types, agent classes, date range, format (JSON/CSV) → "Generate Export" → Celery task → download when ready |
| **Admin-only** | Export requires `admin` or `editor` role |

### 25.8 Approvals (`/approvals`)

| Aspect | Detail |
|---|---|
| **Purpose** | Review and resolve pending approval requests |
| **API calls** | `GET /approvals`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/deny` |
| **List view** | Table: agent, capability, server, params summary, requested at, status badge, actions |
| **Filters** | Status (pending/approved/denied), agent class, capability |
| **Empty state** | "No pending approvals." |
| **Approval action** | Click "Review" → side panel: full request context (agent, capability, params, server, trust level, requested timestamp) → textarea for approver note → "Approve" or "Deny" button |
| **Bulk actions** | Checkbox selection → "Approve Selected" or "Deny Selected" (for low-risk patterns) |

### 25.9 Capability Packs (`/packs`)

| Aspect | Detail |
|---|---|
| **Purpose** | Create and manage curated capability bundles |
| **API calls** | `GET /packs`, `POST /packs`, `DELETE /packs/{id}`, `POST /packs/{id}/assign` |
| **List view** | Cards: pack name, description, capability count, assigned classes count |
| **Empty state** | "No capability packs. Create your first pack to curate capability access." |
| **Create/Edit flow** | Modal: name, description, team namespace → capability picker (search/filter from catalog, multi-select) → save |
| **Detail view** | Assigned capabilities list, assigned agent classes list, usage stats (which agents use this pack) |

### 25.10 Alerts (`/alerts`)

| Aspect | Detail |
|---|---|
| **Purpose** | Configure alert rules, view alert history |
| **API calls** | `GET /alerts` (events), `POST /alerts` (rules — future) |
| **Alert history** | Table: fired at, rule name, message, acknowledged? (icon), acknowledged by |
| **Empty state** | "No alerts fired." |
| **Filter** | Alert type, time range, acknowledged/unacknowledged |

### 25.11 Admin Users (`/admin/users`)

| Aspect | Detail |
|---|---|
| **Purpose** | Manage admin UI users, roles, and access |
| **API calls** | Admin user CRUD (not yet defined in API — to be added) |
| **List view** | Table: username, email, role badge, team scope, MFA status icon, last login, status |
| **Empty state** | "No admin users. You are the first." (first user is auto-created as admin) |
| **Invite flow** | Modal: email, role, team namespace → "Send Invite" → user receives email with setup link |
| **Deactivate** | Confirm dialog → user status "deactivated", sessions revoked |

### 25.12 Trust Posture (`/trust`)

| Aspect | Detail |
|---|---|
| **Purpose** | At-a-glance security posture of all servers |
| **API calls** | `GET /servers` (with trust/health filters) |
| **View** | Grid of server cards colored by trust level: trusted (green), restricted (yellow), approval-gated (orange), unreviewed (red) |
| **Unreviewed count** | Prominent banner: "3 servers unreviewed (oldest: 72 hours)" with link to review |
| **Actions** | Click card → quick trust change dropdown, or navigate to server detail |

---

## 26. Release Management

### 26.1 Semantic Versioning Policy

```
MAJOR.MINOR.PATCH  (e.g., 0.1.0)

MAJOR (X.0.0): Breaking changes
  - Removed endpoints or fields
  - Changed field types
  - Changed error response format
  - Dropped database columns/tables
  - Changed authentication mechanism

MINOR (0.X.0): New features, backward-compatible
  - New endpoints
  - New optional request fields
  - New response fields
  - New database tables/columns
  - New OPA policy rules

PATCH (0.0.X): Bug fixes, backward-compatible
  - Bug fixes
  - Performance improvements
  - Dependency updates (non-breaking)
  - Documentation updates
```

### 26.2 Release Checklist

```markdown
## vX.Y.Z Release Checklist

### Pre-release
- [ ] All CI checks pass (lint, test-sqlite, test-postgres, opa-tests, typecheck, ui-lint)
- [ ] CHANGELOG.md updated with all changes since last release
- [ ] Migration tested: `alembic upgrade head && alembic downgrade -1` (both SQLite + PostgreSQL)
- [ ] OPA policy tests pass: `opa test policies/ -v`
- [ ] Security scan passes: `pip-audit`, `npm audit`
- [ ] Breaking changes documented in CHANGELOG (if any)
- [ ] API diff reviewed (compare OpenAPI specs): no unexpected breaking changes

### Release
- [ ] Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] Push tag: `git push origin vX.Y.Z`
- [ ] GitHub Release created with CHANGELOG notes
- [ ] Docker image built and pushed to ghcr.io
- [ ] PyPI package published: `poetry publish`

### Post-release
- [ ] Verify: `docker pull ghcr.io/deghosal-2026/mcp-fabric:vX.Y.Z`
- [ ] Verify: `pip install mcp-fabric==X.Y.Z`
- [ ] Smoke test: deploy to staging, run capability request
- [ ] Announce in GitHub Discussions
```

### 26.3 PyPI Metadata

```toml
# pyproject.toml (additional fields for PyPI)
[tool.poetry]
name = "mcp-fabric"
version = "0.1.0"
description = "Composable tool mesh for MCP ecosystems"
authors = ["Debashish Ghosal <debashish@ghosal.dev>"]
license = "MIT"
readme = "README.md"
repository = "https://github.com/deghosal-2026/mcp-fabric"
documentation = "https://github.com/deghosal-2026/mcp-fabric#readme"
keywords = ["mcp", "agent", "governance", "platform", "tool-mesh", "ai"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
]

[tool.poetry.scripts]
fabric-admin = "api.cli:main"   # CLI tool for backup/restore/migrations
```

### 26.4 Docker Image Tagging

| Tag | Purpose |
|---|---|
| `v0.1.0` | Specific release version (immutable) |
| `v0.1` | Latest patch in 0.1.x series (moving) |
| `v0` | Latest minor in 0.x series (moving) |
| `latest` | Latest stable release (moving) |

```yaml
# Docker image: ghcr.io/deghosal-2026/mcp-fabric
# Pull examples:
#   ghcr.io/deghosal-2026/mcp-fabric:v0.1.0   (pinned)
#   ghcr.io/deghosal-2026/mcp-fabric:v0.1     (patch auto-update)
#   ghcr.io/deghosal-2026/mcp-fabric:latest   (always latest)
```

### 26.5 CHANGELOG Format

```markdown
# Changelog

## [0.2.0] — 2026-09-15

### Added
- Capability packs: create curated bundles, assign to agent classes (#42)
- Conflict detection: flag overlapping capability mappings (#45)
- Routing rules: explicit server preferences for capability conflicts (#46)
- Server decommission: phased sunset with dependency report (#48)
- Capability deprecation: grace period with migration guidance (#49)
- Schema diff on server re-inspect (#50)

### Changed
- Policy engine: migrated from embedded Python rules to OPA (#55)

### Fixed
- Race condition in batch request when two requests target same server (#60)

## [0.1.0] — 2026-08-15

### Added
- Initial release: server registry, capability catalog, routing engine
- OPA policy engine integration
- Agent authentication and capability surface
- Audit pipeline with structured events
- Admin UI (dashboard, servers, capabilities, audit, approvals)
- Health checks and Prometheus metrics
```

---

## 27. Dependency Management

### 27.1 Dependabot Configuration

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "America/Los_Angeles"
    open-pull-requests-limit: 5
    labels: ["dependencies", "python"]
    versioning-strategy: "lockfile-only"
    groups:
      fastapi:
        patterns: ["fastapi", "uvicorn", "starlette"]
      sqlalchemy:
        patterns: ["sqlalchemy", "alembic", "aiosqlite", "asyncpg"]
      telemetry:
        patterns: ["prometheus-client", "opentelemetry-*"]
      testing:
        patterns: ["pytest*", "httpx"]
      linting:
        patterns: ["ruff"]

  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels: ["dependencies", "docker"]

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels: ["dependencies", "ci"]

  - package-ecosystem: "npm"
    directory: "/ui"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
    labels: ["dependencies", "ui"]
    groups:
      react:
        patterns: ["react", "react-dom", "@types/react*"]
      tanstack:
        patterns: ["@tanstack/*"]
      vite:
        patterns: ["vite", "@vitejs/*"]
```

### 27.2 Dependency Update Cadence

| Type | Frequency | Auto-merge? |
|---|---|---|
| Patch updates | Weekly (Dependabot) | Yes (if CI passes) |
| Minor updates | Weekly (Dependabot) | Manual review |
| Major updates | Manual | Manual review + migration plan |
| Security patches | Immediate (Dependabot security) | Yes (if CI passes) |

### 27.3 Lockfile Strategy

```
Poetry lock file (poetry.lock): committed to repo
  → Deterministic builds in CI and production
  → Dependabot opens PRs with updated lockfiles
  → CI validates: all tests pass with updated deps

npm lock file (package-lock.json): committed to repo
  → Same strategy for UI dependencies
```

### 27.4 Vulnerability Scanning

```yaml
# Automated scanning:
# - Dependabot security alerts: enabled (GitHub default)
# - pip-audit: runs in CI on every PR
# - npm audit: runs in CI on every PR

# CI step:
- run: pip-audit
- run: cd ui && npm audit --audit-level=high
# Fails CI if high/critical vulnerabilities found
```

---

## 28. Load Testing Strategy

### 28.1 Load Test Scenarios

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class FabricUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def capability_request(self):
        """Simulate agent making capability requests (most common)."""
        self.client.post("/v1/capability/request",
            headers={"Authorization": f"Bearer {self.token}",
                     "Accept": "application/vnd.fabric.v1+json"},
            json={"capability": "code:search",
                  "params": {"query": "deployment", "max_results": 5}}
        )

    @task(1)
    def batch_request(self):
        """Simulate incident agent making batch requests."""
        self.client.post("/v1/capability/batch",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"requests": [
                {"id": "1", "capability": "code:search", "params": {"query": "test"}},
                {"id": "2", "capability": "knowledge:search", "params": {"query": "runbook"}},
                {"id": "3", "capability": "dependency:list", "params": {"service": "api"}}
            ]}
        )

    @task(1)
    def health_check(self):
        self.client.get("/v1/health")
```

### 28.2 Load Test Targets (per scenario)

| Scenario | Target RPS | Max p95 latency | Max error rate |
|---|---|---|---|
| Capability request | 500 | < 500ms | < 0.1% |
| Batch request (3) | 150 | < 800ms | < 0.1% |
| Agent connect | 200 | < 100ms | < 0.1% |
| Mixed workload (70% request, 15% batch, 10% connect, 5% health) | 800 total | varies | < 0.5% |

### 28.3 Load Test Procedure

```bash
# 1. Deploy Fabric to test environment (matching production config)
docker-compose -f docker-compose.prod.yml up -d

# 2. Register test servers and seed test data
poetry run python tests/load/seed.py --servers 10 --capabilities 30 --agents 50

# 3. Run Locust (headless)
locust -f tests/load/locustfile.py \
  --host http://localhost:8000 \
  --users 500 \
  --spawn-rate 50 \
  --run-time 10m \
  --headless \
  --csv results/

# 4. Analyze results
# Check: p95 latency, error rate, RPS achieved
# Compare against performance targets (Section 23)
# If below target: investigate bottlenecks (DB, OPA, MCP server latency)
```

### 28.4 Chaos Testing (Failure Injection)

```python
# tests/chaos/chaos.py — scenarios for failure injection

# Scenario 1: MCP server timeout
# - Simulate a registered MCP server that responds slowly (>5s)
# - Verify: Fabric times out at 5s, falls back, logs degradation, alerts fire

# Scenario 2: PostgreSQL restart
# - Restart PostgreSQL while Fabric is serving traffic
# - Verify: Fabric returns 503 during outage, recovers within 10s of DB coming back
# - Verify: No data loss, all state intact

# Scenario 3: Redis restart
# - Restart Redis while Fabric is serving traffic
# - Verify: Agent sessions expire gracefully (agents re-authenticate)
# - Verify: Rate limiting pauses (allows through during Redis outage, recovers)
# - Verify: Health checks pause, resume within 30s

# Scenario 4: OPA failure
# - Stop OPA while Fabric is serving traffic
# - Verify: Fabric returns 503 for capability requests (cannot evaluate policy)
# - Verify: Deny-by-default — no requests pass without policy evaluation

# Scenario 5: Single API instance failure
# - Kill one of N API instances behind load balancer
# - Verify: Traffic shifts to remaining instances
# - Verify: No dropped requests (connection refused → LB retries)
```

---

## 29. Development Setup

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

---

## 30. Dockerfile Specification

### 30.1 API Dockerfile

```dockerfile
# Stage 1: Build
FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.8.3

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Stage 2: Runtime
FROM python:3.12-slim-bookworm AS runtime

RUN groupadd --system fabric && useradd --system --gid fabric --no-create-home fabric

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY --chown=fabric:fabric . .

USER fabric

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

ENTRYPOINT ["uvicorn", "api.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 30.2 UI Dockerfile

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app
COPY ui/package.json ui/package-lock.json ./
RUN npm ci

COPY ui/ ./
RUN npm run build

# Stage 2: Serve
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

### 30.3 Image Security

```bash
# Scan images before pushing
docker scan mcp-fabric:latest          # Docker Scout / Snyk
trivy image mcp-fabric:latest          # Aqua Trivy (OSS)

# Base image considerations:
# - python:3.12-slim-bookworm: ~50MB smaller than full image, fewer CVEs
# - nginx:1.27-alpine: ~5MB, minimal attack surface
# - Non-root user (fabric) for API — no privilege escalation
# - No dev dependencies in runtime image (Poetry --only main)
# - apt cache cleaned in builder stage
```

---

## 31. Middleware Pipeline Order

The order is critical — each middleware depends on the previous.

```python
# api/main.py — middleware registration order
app = FastAPI()

# 1. CORS (outermost — must run before auth for preflight OPTIONS)
app.add_middleware(CORSMiddleware, allow_origins=[...])

# 2. Request ID (assigns unique ID to every request for tracing)
app.add_middleware(RequestIDMiddleware)

# 3. Tracing (starts OpenTelemetry span, includes request_id)
app.add_middleware(TracingMiddleware)

# 4. Authentication (validates Bearer token or admin session)
#    Must run BEFORE rate limiting — unauthenticated requests should hit auth, not rate limit
#    Rate limiting for unauthenticated requests is handled at the network/LB level
app.add_middleware(AuthMiddleware)

# 5. Tenant scoping (reads agent_class → sets namespace filter)
#    Must run AFTER auth — depends on request.state.agent_identity
app.add_middleware(TenantMiddleware)

# 6. Rate limiting (per-agent, after identity is known)
app.add_middleware(RateLimitMiddleware)

# 7. Audit (logs request start/end — wraps the entire handler)
#    Runs as a background task after the response to avoid adding latency
app.add_middleware(AuditMiddleware)
```

**Rationale for this order:**

| Position | Middleware | Why this position |
|---|---|---|
| 1 | CORS | Must handle preflight OPTIONS before any auth/rate limiting |
| 2 | Request ID | Earliest possible — every subsequent middleware/log gets the ID |
| 3 | Tracing | Starts span as early as possible to capture full request duration |
| 4 | Auth | Validates identity before letting the request consume rate limit budget |
| 5 | Tenant | Depends on auth result (agent_class → namespace) |
| 6 | Rate Limit | After identity is known — per-agent counters |
| 7 | Audit | Outermost after handler — captures full request + response |

**Anti-patterns avoided:**
- Rate limit before auth → attackers can DoS with bogus tokens, consuming rate limit counters
- Tenant before auth → no identity to scope by
- Audit before handler → adds latency to every request (use background task instead)

---

## 32. Pydantic Models (Core Schemas)

### 32.1 Capability Request

```python
# api/models/capability.py
from pydantic import BaseModel, Field
from typing import Any
from uuid import UUID

class CapabilityRequest(BaseModel):
    capability: str = Field(..., pattern=r"^[a-z]+:[a-z][a-z-]*$",
        examples=["code:search", "incident:get"])
    params: dict[str, Any] = Field(default_factory=dict,
        examples=[{"query": "deployment", "max_results": 5}])

class BatchCapabilityRequest(BaseModel):
    requests: list[BatchRequestItem] = Field(..., min_length=1, max_length=10)

class BatchRequestItem(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    capability: str = Field(..., pattern=r"^[a-z]+:[a-z][a-z-]*$")
    params: dict[str, Any] = Field(default_factory=dict)

class CapabilityResponse(BaseModel):
    status: str  # "success" | "approval_pending" | "error"
    data: dict[str, Any] | None = None
    server: str | None = None
    routing_reason: str | None = None
    fallback_used: bool = False
    latency_ms: int | None = None

class BatchResponse(BaseModel):
    results: list[BatchResultItem]

class BatchResultItem(BaseModel):
    id: str
    status: str
    data: dict[str, Any] | None = None
    server: str | None = None
    error: str | None = None
    latency_ms: int | None = None
```

### 32.2 Server

```python
# api/models/server.py
class ServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    endpoint: str = Field(..., pattern=r"^https?://")
    owner_team: str | None = None
    description: str | None = None
    labels: list[str] = Field(default_factory=list)
    team_namespace: str | None = None

class ServerResponse(BaseModel):
    id: UUID
    name: str
    endpoint: str
    owner_team: str | None
    description: str | None
    labels: list[str]
    trust_level: str  # "unreviewed" | "trusted" | "restricted" | "approval-gated"
    health_status: str  # "healthy" | "degraded" | "unhealthy" | "unknown"
    last_health_check: datetime | None
    team_namespace: str | None
    tools: list[ToolResponse] = Field(default_factory=list)
    registered_at: datetime
    decommissioned_at: datetime | None = None

class ServerInspectResponse(ServerResponse):
    tools_added: list[ToolResponse] = Field(default_factory=list)
    tools_removed: list[ToolResponse] = Field(default_factory=list)
    tools_changed: list[ToolChange] = Field(default_factory=list)

class ToolChange(BaseModel):
    tool_name: str
    changes: dict[str, Any]  # added_params, removed_params, changed_output
    is_breaking: bool
```

### 32.3 Error

```python
# api/models/error.py
class FabricError(BaseModel):
    error: str  # error code: "invalid_parameter", "capability_not_found", etc.
    message: str  # human-readable description
    details: dict[str, Any] = Field(default_factory=dict)  # context-specific
    request_id: str

    # Optional hints for agent self-correction
    suggestion: str | None = None  # e.g., "Did you mean 'vulnerability:scan'?"
    retry_after: int | None = None  # seconds for rate limit / degradation
```

### 32.4 Agent Identity

```python
# api/models/agent.py
class AgentIdentityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    agent_class_id: UUID
    rate_limit_per_min: int = Field(default=100, ge=1, le=10000)
    expires_in_days: int | None = Field(default=90, ge=1, le=365)

class AgentIdentityResponse(BaseModel):
    id: UUID
    name: str
    agent_class_id: UUID
    agent_class_name: str
    token_prefix: str  # first 4 chars only — never the full token
    status: str
    rate_limit_per_min: int
    expires_at: datetime | None
    created_at: datetime

class AgentConnectResponse(BaseModel):
    agent_id: str
    agent_class: str
    capability_surface: list[CapabilitySurfaceItem]

class CapabilitySurfaceItem(BaseModel):
    name: str
    trust_level: str
    requires_approval: bool = False
    deprecated: bool = False
```

### 32.5 Audit Event

```python
# api/models/audit.py
class AuditEventResponse(BaseModel):
    id: UUID
    event_type: str
    actor_type: str
    actor_id: str | None
    target_type: str | None
    target_id: str | None
    details: dict[str, Any]
    created_at: datetime

class AuditExportRequest(BaseModel):
    from_date: date
    to_date: date
    event_types: list[str] | None = None
    agent_classes: list[str] | None = None
    format: str = Field(default="json", pattern="^(json|csv)$")
```

---

## 33. SLO Definitions

### 33.1 Service Level Objectives

| SLO | Target | Measurement Window | Error Budget (monthly) |
|---|---|---|---|
| **Availability** | 99.9% | 30 days | 43m 12s downtime |
| **Latency (p95)** | < 500ms for capability requests | 30 days | 5% of requests may exceed |
| **Latency (p99)** | < 2s for capability requests | 30 days | 1% of requests may exceed |
| **Correctness** | > 99.5% of routed requests go to correct server | 30 days | 0.5% may be misrouted |
| **Freshness** | Server health state stale by < 60s | Rolling 5m | Health checks every 30s |
| **Durability** | < 30s data loss on PostgreSQL failure | Per incident | WAL archiving continuous |

### 33.2 SLI Measurement

```python
# Availability SLI
#   Measured: (successful_requests / total_requests) over 30d window
#   "Successful" = 2xx or 4xx (client errors are not Fabric's fault)
#   5xx = Fabric's fault → counts against error budget

# Latency SLI
#   Measured: histogram_quantile(0.95, fabric_request_duration_seconds) over 30d
#   Latency = total time from request receipt to response sent
#   Includes: routing + policy + server call + normalization

# Correctness SLI
#   Measured: manual evaluation of 100 random requests/week
#   Human evaluator checks: was the correct server chosen?
#   Automated in v0.2.0 via golden test set
```

### 33.3 Error Budget Policy

```
When error budget remaining > 50%:
  → Normal operations. Ship features freely.

When error budget remaining 20-50%:
  → Caution. Postpone risky deployments. Focus on reliability.

When error budget remaining < 20%:
  → Freeze all non-critical deployments.
  → All engineering time goes to reliability improvements.
  → Escalate to platform lead.

When error budget exhausted (0%):
  → Incident declared.
  → Feature freeze until SLO is met again for 7 consecutive days.
```

### 33.4 Alerting Thresholds (tied to SLOs)

| Alert | Threshold | Severity | Action |
|---|---|---|---|
| Error budget burn rate > 5x | Burned 10% in 1 hour | P0 | Page on-call immediately |
| Error budget burn rate > 2x | Burned 5% in 6 hours | P1 | Page on-call, investigate |
| p95 latency > 1s for 10 min | 2x SLO target | P1 | Page on-call |
| Availability drops below 99% | 30m window | P0 | Page on-call immediately |
| Error budget < 10% remaining | End of month projection | P2 | Notify platform lead, freeze deployments |
```

---

## 34. Development Setup
```
