# MCP Fabric — Design Document

> **Status:** Draft v1.0  
> **Last updated:** 2026-07-22  
> **Covers:** Auth design, state machines, sequence diagrams, caching, concurrency model

---

## 1. Authentication Design

### 1.1 Agent Token Lifecycle

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Created  │───▶│ Active   │───▶│ Rotated  │───▶│ Expired  │
│ (token   │    │ (normal  │    │ (grace   │    │ (past    │
│  returned│    │  use)    │    │  period) │    │  expiry) │
│  once)   │    └────┬─────┘    └────┬─────┘    └──────────┘
└──────────┘         │               │
                     │               │ (grace period ends)
                     │               ▼
                     │         ┌──────────┐
                     └────────▶│ Revoked  │ (manual, any time)
                               │ (immediate│
                               │  rejection)│
                               └──────────┘
```

**Create:** Admin generates token for agent identity. Fabric returns full token ONCE. Stores `bcrypt(token_salt=12, token)` hash + first 4 chars as `token_prefix` for UI display. Never stores full token.

**Active:** Agent sends `Authorization: Bearer fcp_xxxx...`. Fabric hashes incoming token, compares against stored hash. Redis caches validation result (key: `fcp:auth:{token_hash}`, TTL: 5 min).

**Rotate:** Admin initiates rotation → Fabric generates new token. Sets `grace_period_end = now + configurable hours` on old token. Agent has until grace period ends to pick up new token. Both old and new tokens are valid during grace period.

**Revoke:** Admin revokes immediately → `status = revoked`, `revoked_at = now()`. Redis cache entry deleted. All active sessions invalidated on next request (401).

**Expire:** Token passes `expires_at`. Returns 401 with `token_expired` error code. Grace period does not extend beyond `expires_at`.

### 1.2 Admin Authentication Flow

```
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌──────────────┐
│  Login   │────▶│ Password │────▶│   MFA   │────▶│   Session    │
│  Page    │     │  Check   │     │  Check  │     │   (JWT in    │
│          │     │ (bcrypt) │     │  (TOTP) │     │    Redis)    │
└─────────┘     └────┬─────┘     └────┬────┘     └──────┬───────┘
                     │               │                  │
                     │ (fail)        │ (fail)           │ (expiry/logout)
                     ▼               ▼                  ▼
              ┌──────────┐   ┌──────────┐       ┌──────────┐
              │ Account  │   │ MFA      │       │ Session  │
              │ Locked   │   │ Failed   │       │ Ended    │
              │ (15 min) │   │ (retry)  │       │          │
              └──────────┘   └──────────┘       └──────────┘
```

**Invite:** Admin creates user with email + role + (optional) team namespace. User receives email with one-time setup link. Link expires in 24 hours.

**Setup:** User clicks link → sets password (min 12 chars, 1 uppercase, 1 number, 1 special). Optionally sets up MFA (TOTP — Google Authenticator compatible). Receives backup codes (8 codes, one-time use each).

**Login:** User enters credentials → Fabric validates password via bcrypt. If MFA enabled: prompts for TOTP code. On success: issues JWT (claims: user_id, role, team_namespace, exp=8h). JWT stored in Redis with TTL.

**Session:** Every admin UI request validates JWT signature + expiry + Redis presence. Session TTL resets on activity (sliding expiration). Concurrent sessions limited to 3 per user.

**Logout:** Deletes Redis key. JWT is stateless but Redis check ensures immediate invalidation.

**Deactivation:** Admin deactivates user → status=deactivated. All Redis sessions deleted. User cannot log in. Audit events preserved.

### 1.3 MFA Setup and Recovery

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Enable  │────▶│  Verify  │────▶│  Backup  │
│  MFA     │     │  TOTP    │     │  Codes   │
│ (QR code)│     │  Code    │     │ (shown   │
│          │     │          │     │  once)   │
└──────────┘     └──────────┘     └──────────┘
```

**Enable:** User clicks "Enable MFA" → Fabric generates TOTP secret → shows QR code → user scans with authenticator app → enters code to verify → Fabric stores encrypted secret → shows 8 backup codes (one-time download).

**Recovery:** User loses MFA device → clicks "Lost MFA device?" on login → enters backup code → Fabric invalidates MFA → user must re-enable MFA. Admin can also reset MFA for any user (logged as admin audit event).

**Backup codes:** 8 codes, 8 chars each. Stored as `bcrypt(code)` hashes. Each code usable once. After all 8 used: MFA is disabled, user must re-enable.

### 1.4 Password Policy

| Rule | Value |
|---|---|
| Minimum length | 12 characters |
| Complexity | 1 uppercase, 1 lowercase, 1 digit, 1 special character |
| Maximum age | 90 days (advisory — not enforced in v0.1.0) |
| History | Last 5 passwords cannot be reused |
| Lockout | 5 failed attempts → 15 minute account lock |
| Reset | Email-based reset link, expires in 1 hour |

### 1.5 Auth Audit Events

| Event | Logged Data |
|---|---|
| `admin_login` | user_id, IP, user_agent, success/fail |
| `admin_logout` | user_id, session_duration |
| `admin_mfa_setup` | user_id |
| `admin_mfa_recovery` | user_id, backup_code_used |
| `admin_account_locked` | user_id, failed_attempts |
| `token_created` | admin_user_id, agent_name, agent_class |
| `token_rotated` | admin_user_id, agent_name, grace_period_hours |
| `token_revoked` | admin_user_id, agent_name, reason |
| `agent_connect` | agent_id, agent_class, IP (not logged at INFO — DEBUG only to avoid volume) |

---

## 2. State Machines

### 2.1 MCP Server States

```
                    ┌──────────┐
                    │ Registered│ (new)
                    └────┬─────┘
                         │ health check passes
                         ▼
              ┌─────────────────────┐
              │      Healthy         │◄──────────────────────────┐
              │ (health check OK)    │                           │
              └──────┬──────┬───────┘                           │
                     │      │                                    │
        (timeout)    │      │ (fallback events)                  │
                     ▼      ▼                                    │
              ┌──────────┐ ┌───────────┐                         │
              │ Unhealthy│ │ Degraded  │ (some tools failing)    │
              │ (all     │ │ (partial  │                         │
              │  tools   │ │  failures)│─────────────────────────┘
              │  fail)   │ └───────────┘   (recovery)
              └──────────┘
                     │
                     │ (persistent failure)
                     ▼
              ┌──────────────────────────────────────────────┐
              │              Decommissioning                  │
              │                                              │
              │  grace_period ──▶ migration ──▶ sunset       │
              │  (deprecation   (redirect to   (removed from  │
              │   header added)  replacement)    registry)    │
              └──────────────────────────────────────────────┘
```

### 2.2 Capability States

```
┌──────────┐     ┌─────────────┐     ┌──────────┐
│  Active  │────▶│ Deprecated  │────▶│ Retired  │
│ (normal  │     │ (grace      │     │ (removed │
│  use)    │     │  period)    │     │  from    │
│          │     │             │     │  catalog)│
└──────────┘     └──────┬──────┘     └──────────┘
                        │
                        │ (grace period ends)
                        ▼
                  ┌──────────┐
                  │ Retired  │ (410 Gone)
                  └──────────┘
```

### 2.3 Approval States

```
┌──────────┐
│ Pending  │ (approval-gated request created)
└────┬─────┘
     │
     ├──▶ ┌──────────┐
     │    │ Approved │ (human approves → request routed)
     │    └──────────┘
     │
     ├──▶ ┌──────────┐
     │    │ Denied   │ (human denies → 403 to agent)
     │    └──────────┘
     │
     └──▶ ┌──────────┐
          │ Expired  │ (no action within TTL → auto-deny)
          └──────────┘
```

### 2.4 Agent Token States

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Active  │────▶│ Rotating │────▶│  Active  │ (new token)
│ (primary │     │ (grace   │     │ (primary │
│  token)  │     │  period) │     │  token)  │
└────┬─────┘     └──────────┘     └──────────┘
     │
     ├──▶ ┌──────────┐
     │    │ Revoked  │ (admin action, immediate)
     │    └──────────┘
     │
     └──▶ ┌──────────┐
          │ Expired  │ (past expires_at)
          └──────────┘
```

### 2.5 Alert States

```
┌──────────┐     ┌───────────────┐     ┌──────────┐
│  Fired   │────▶│ Acknowledged  │────▶│ Resolved │
│ (alert   │     │ (human saw    │     │ (root    │
│  rule    │     │  and ack'd)   │     │  cause   │
│  matched)│     │               │     │  fixed)  │
└──────────┘     └───────────────┘     └──────────┘
```

---

## 3. Sequence Diagrams

### 3.1 Approval-Gated Capability Request

```
Agent           Fabric API        OPA         Approval Queue    Human Admin     MCP Server
  │                 │              │               │                │               │
  │── POST request ─▶              │               │                │               │
  │                 │── eval ─────▶│               │                │               │
  │                 │◀─ gated ────│               │                │               │
  │                 │── create approval ────────▶│                │               │
  │                 │── notify (Celery) ────────────────────────▶│                │
  │◀── 202 pending ─│              │               │                │               │
  │                 │              │               │                │               │
  │  (agent polls)  │              │               │                │               │
  │── GET /status ─▶│              │               │                │               │
  │◀── "pending" ───│              │               │                │               │
  │                 │              │               │                │               │
  │                 │              │               │◀── review ─────│               │
  │                 │              │               │── approve ───▶│               │
  │                 │◀── approved ────────────────│                │               │
  │                 │── route request ───────────────────────────────────────────▶│
  │                 │◀── response ──────────────────────────────────────────────│
  │                 │── log audit ──│               │                │               │
  │◀── 200 + result─│              │               │                │               │
```

### 3.2 Server Failover

```
Agent           Fabric API       Router        MCP Client      Primary Srv     Fallback Srv    Platform Team
  │                 │              │               │                │               │               │
  │── POST ───────▶│              │               │                │               │               │
  │                 │── select ──▶│               │                │               │               │
  │                 │◀── primary──│               │                │               │               │
  │                 │── call ────────────────────▶│── call ───────▶│               │               │
  │                 │              │               │   [timeout]    │               │               │
  │                 │              │               │◀── error ─────│               │               │
  │                 │              │               │── fallback ─────────────────▶│               │
  │                 │              │               │◀── response ─────────────────│               │
  │                 │── mark degraded + log ──────│                │               │               │
  │                 │── normalize ─│               │                │               │               │
  │                 │── check alert threshold ───────────────────────────────────────────────────▶│
  │◀── 200 (fallback)              │               │                │               │               │
```

### 3.3 Batch Request (Mixed Success/Failure)

```
Agent           Fabric API       Router        MCP Client      Server A       Server B       Server C
  │                 │              │               │               │              │              │
  │── POST batch ─▶│              │               │               │              │              │
  │  [req-1, req-2, │              │               │               │              │              │
  │   req-3]        │              │               │               │              │              │
  │                 │              │               │               │              │              │
  │                 │── resolve all 3 ───────────▶│               │              │              │
  │                 │              │               │               │              │              │
  │                 │              │               │── call req-1 ─▶              │              │
  │                 │              │               │── call req-2 ──────────────▶│              │
  │                 │              │               │── call req-3 ────────────────────────────▶│
  │                 │              │               │   (parallel)    │              │              │
  │                 │              │               │               │              │              │
  │                 │              │               │◀── 200 ───────│              │              │
  │                 │              │               │◀── 200 ─────────────────────│              │
  │                 │              │               │◀── timeout ──────────────────────────────│
  │                 │              │               │               │              │              │
  │                 │              │               │── fallback req-3 ──────────▶│ (retry)      │
  │                 │              │               │◀── 200 ─────────────────────│              │
  │                 │              │               │               │              │              │
  │                 │── normalize all ────────────│               │              │              │
  │                 │── log audit   │               │               │              │              │
  │◀── 200 batch results           │               │               │              │              │
  │  [{ok}, {ok}, {ok, fallback}]  │               │               │              │              │
```

---

## 4. Caching Strategy

### 4.1 What Gets Cached

| Data | Cache Store | TTL | Invalidation | Rationale |
|---|---|---|---|---|
| Agent token validation | Redis | 5 min | Token revocation clears cache | Avoids bcrypt on every request |
| Agent capability surface | Redis | 5 min | Token rotation, policy changes | Avoids multi-table JOIN per request |
| OPA decision (agent_class, server, capability) | Redis | 60 sec | Policy bundle deploy | OPA eval is ~15ms — caching saves 10ms |
| Capability catalog (full) | Redis | 30 sec | Capability create/update/deprecate | Read-heavy, write-light. Catalog changes are rare. |
| Server registry (full) | Redis | 30 sec | Server register/decommission/health change | Read-heavy. Routing engine reads registry on every request. |
| Rate limit counters | Redis (INCR) | 1 min window | Auto-expire | Atomic counters, no DB needed |
| Server health state | Redis | Ephemeral | Celery health check overwrites | Health is volatile — Redis is the source of truth |
| Admin UI session | Redis | 8h (sliding) | Logout, deactivation | JWT is stateless but Redis enables instant invalidation |

### 4.2 What Is NOT Cached

| Data | Why Not Cached |
|---|---|
| Audit events | Immutable log — caching would lead to stale query results |
| Approval requests | Must reflect real-time state (pending → approved/denied) |
| Agent identity tokens (full) | Never stored. Only bcrypt hashes are stored. |
| MCP server tool call responses | Fabric is a routing layer, not a response cache |

### 4.3 Cache Invalidation Patterns

```
Cache-Aside (most common):
  1. Read: check Redis → miss → query DB → populate Redis → return
  2. Write: update DB → delete Redis key (invalidate) → next read populates fresh data

Write-Through (server health):
  1. Celery health checker pings server → writes status to Redis directly
  2. Routing engine reads from Redis (never queries DB for health)

TTL-Based (OPA decisions):
  1. Cache with 60s TTL — natural expiry, no invalidation needed
  2. Policy bundle deploy: delete all OPA cache keys (prefix: fcp:opa:*)
```

---

## 5. Concurrency Model

### 5.1 Async I/O Model

Fabric uses Python `asyncio` throughout. The FastAPI app runs on `uvicorn` with multiple workers. Each worker is single-threaded, event-loop-driven.

```
┌─────────────────────────────────────────────────────┐
│                   Uvicorn (4 workers)                │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐│
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │  │ Wkr 4││
│  │ (async)  │  │ (async)  │  │ (async)  │  │(asnc)││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──┬───┘│
│       │             │             │           │     │
└───────┼─────────────┼─────────────┼───────────┼─────┘
        │             │             │           │
        └─────────────┴─────────────┴───────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
    ┌─────────▼─────────┐  ┌─────────▼─────────┐
    │  PostgreSQL Pool   │  │   Redis Pool      │
    │  (20 connections)  │  │  (20 connections) │
    └───────────────────┘  └───────────────────┘
```

### 5.2 Connection Pooling

```python
# PostgreSQL: SQLAlchemy async engine with connection pool
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,         # Base pool size per worker
    max_overflow=10,      # Up to 10 extra under load
    pool_recycle=3600,    # Recycle connections after 1 hour
    pool_pre_ping=True    # Verify connection before use
)

# Redis: redis.asyncio connection pool
redis = redis.asyncio.Redis(
    connection_pool=redis.asyncio.ConnectionPool(
        max_connections=20,
        timeout=5
    )
)
```

### 5.3 Request Concurrency

Each `uvicorn` worker handles concurrent requests via `asyncio` cooperative multitasking. When a request awaits I/O (DB query, MCP server call, Redis operation), the event loop switches to another request. This means a single worker can handle hundreds of concurrent requests with no thread overhead.

```python
# A single worker:
# Request 1: ──await DB── await MCP call ──await DB── return
# Request 2:    ──await DB── return
# Request 3:       ──await DB── await Redis ──return
# Request 4:          ──await OPA ──return
#                 ↑ time ────────────────────────────▶
# All 4 requests make progress concurrently on one thread
```

### 5.4 Thread Safety

Fabric is designed for **shared-nothing workers**. Each worker has its own connection pool. The only shared state is PostgreSQL (ACID-safe) and Redis (atomic operations).

**What IS thread-safe:**
- PostgreSQL: ACID transactions, row-level locking for concurrent writes
- Redis: INCR, SET NX, LPUSH are atomic
- SQLAlchemy async sessions: session-per-request pattern, never shared across requests

**What is NOT shared and therefore doesn't need locking:**
- Request-scoped data (request.state)
- Local caches (not used — all caching is in Redis)
- In-memory counters (not used — Prometheus client handles metric aggregation)

### 5.5 Race Condition Mitigations

| Scenario | Risk | Mitigation |
|---|---|---|
| Two admins decommission same server | Double sunset | DB row-level lock (SELECT FOR UPDATE) |
| Token rotation + revocation race | Token state confusion | DB transaction — rotate then revoke is atomic |
| Concurrent health checks on same server | Stale health state | Celery beat schedules once — single worker per beat |
| Capability creation + deprecation race | Active + deprecated | DB unique constraint — no two states simultaneously |
| Approval + timeout race | Pending → approved → expired | `UPDATE WHERE status='pending'` — only pending approvals are mutable |

### 5.6 Graceful Degradation

```
Priority order during overload:
1. Health checks continue (critical for load balancer)
2. Capability requests continue (core product)
3. Admin UI requests continue (reduced priority)
4. Audit export generation pauses (Celery task backpressure)
5. Webhook deliveries pause (retry later)

Implemented via:
- Uvicorn backlog: 2048 connections (OS-level queuing)
- FastAPI timeout: 30s per request (prevent hanging connections)
- Celery concurrency: 4 workers per worker process (limit DB connections)
- Load shedding: return 503 if Redis/PostgreSQL pool is exhausted
```

---

## 6. Related Documents

- `docs/PRD.md` — Product requirements (WHY, WHAT, user journeys)
- `docs/spec.md` — Technical specification (HOW, API contracts, DB schema)
- `docs/ARCHITECTURE.md` — Architecture overview, component responsibilities
