# Security Guide

Security architecture, authentication model, and operational procedures for MCP Fabric.

## Agent Authentication Model

### Token Lifecycle

Agents authenticate using bearer tokens (JWT format) with the following lifecycle:

```
Created → Active → Rotated (grace period) → Expired
              ↘ Revoked (immediate, any time)
```

**Create:** Admin generates a token for an agent identity. The full token is returned **once** at creation. Fabric stores a `bcrypt(rounds=12, token)` hash plus the first 4 characters as `token_prefix` for UI display. The full token is never persisted.

**Active:** Agent sends `Authorization: Bearer fcp_xxxx...`. Fabric hashes the incoming token, compares against the stored hash. Redis caches validation results (`fcp:auth:{token_hash}`, TTL: 5 min) to avoid bcrypt on every request.

**Rotate:** Admin initiates rotation → Fabric generates a new token. Sets `grace_period_end` on the old token. Both tokens are valid during the grace period, allowing agents to pick up the new token without downtime.

**Revoke:** Admin revokes immediately → `status = revoked`, `revoked_at = now()`. Redis cache entry deleted. All active sessions invalidated on next request (401).

**Expire:** Token passes `expires_at`. Returns 401 with `token_expired` error code.

### Token Storage Security

- Full tokens never stored in the database
- Only bcrypt hashes persisted
- Token prefix (first 4 chars) stored for UI identification
- Rate limiting (100 req/min default) prevents brute force of token hashes
- Redis-based authentication cache with 5-minute TTL

## Admin Authentication

### Password Policy

| Rule | Value |
|------|-------|
| Minimum length | 12 characters |
| Complexity | 1 uppercase, 1 lowercase, 1 digit, 1 special character |
| Maximum age | 90 days (advisory — not enforced) |
| History | Last 5 passwords cannot be reused |
| Storage | bcrypt with 12 rounds |

### Multi-Factor Authentication (MFA)

- TOTP-based (Google Authenticator compatible)
- QR code setup flow
- 8 backup codes (bcrypt hashed, one-time use each)
- Admin can reset MFA for any user (audit-logged event)

### Account Lockout

| Condition | Action |
|-----------|--------|
| 5 failed login attempts | 15 minute account lock |
| Lockout during grace period | Countdown continues |
| Lockout escalation | Admin must unlock (audit-logged) |
| Concurrent sessions | Limited to 3 per user |

### Session Management

- JWT with 8-hour expiry (configurable via `ADMIN_SESSION_TTL_HOURS`)
- Sliding expiration (TTL resets on activity)
- Redis-backed session store enables instant invalidation
- Logout deletes Redis key, blacklists JWT
- Deactivation deletes all sessions and prevents future login

## Token Lifecycle Operations

### Create Token

```bash
POST /admin/tokens
Authorization: Bearer <admin-jwt>
Body: {
  "agent_name": "igor-01",
  "agent_class": "agent:incident-responder",
  "expires_in_days": 90
}
Response 201: {
  "token": "fcp_xxxxxxxx...",  // shown once
  "token_id": "uuid",
  "expires_at": "2026-10-21T00:00:00Z"
}
```

### Rotate Token

Extends the grace period window so old and new tokens coexist. Agents can pick up the new token without interruption.

```bash
POST /admin/tokens/{id}/rotate
Body: { "grace_period_hours": 24 }
Response 200: {
  "new_token": "fcp_yyyyyyy...",  // shown once
  "old_token_expires_at": "2026-07-24T00:00:00Z"
}
```

### Revoke Token

Immediate invalidation. All in-flight requests with the old token will fail authentication.

```bash
POST /admin/tokens/{id}/revoke
Body: { "reason": "compromised" }
Response 200: { "status": "revoked", "revoked_at": "..." }
```

## RBAC Roles

| Role | Permissions | Scope |
|------|-------------|-------|
| `admin` | Full control over all resources | Global (all teams) |
| `editor` | Manage servers, policies, capability packs | Team-scoped |
| `viewer` | Read-only access to audit logs, catalog, server inventory | Global (all teams) |

### Team Namespace Scoping

- Admin roles are global by default
- Editor roles are scoped to a `team_namespace` (e.g., `team:platform`)
- Viewers see all resources but cannot modify anything
- Cross-team access returns 403 `namespace_restricted`

## Audit Logging

### Captured Events

| Event Type | Data Logged |
|------------|-------------|
| `capability_request` | agent_id, capability, server_id, latency, outcome |
| `denied_request` | agent_id, capability, policy_rule, reason |
| `admin_login` | user_id, IP, user_agent, success/fail |
| `admin_logout` | user_id, session_duration |
| `token_created` | admin_user_id, agent_name, agent_class |
| `token_rotated` | admin_user_id, agent_name, grace_period |
| `token_revoked` | admin_user_id, agent_name, reason |
| `policy_change` | admin_user_id, policy_before, policy_after |
| `server_registered` | admin_user_id, server_name, endpoint |
| `server_decommission` | admin_user_id, server_name, phases |

### Audit Log Properties

- **Append-only:** `audit_events` table has no UPDATE or DELETE operations
- **Immutable:** Once written, audit records cannot be modified
- **Configurable retention:** Default 90 days via `AUDIT_RETENTION_DAYS`
- **Exportable:** JSON and CSV export for compliance

## XSS Prevention

- React with strict Content Security Policy headers
- All user-provided content is rendered through React's JSX escaping
- API responses use `Content-Type: application/json` (not text/html)
- CSP headers configured in CORSMiddleware:

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
```

## CORS Configuration

Configured via `CORS_ORIGINS` environment variable (default: `http://localhost:3000`).

```python
# api/middleware/cors.py
CORS_CONFIG = {
    "allow_origins": settings.cors_origins,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type", "Accept"],
    "expose_headers": ["Fabric-Request-Id", "Fabric-API-Version"],
    "max_age": 3600,
}
```

Production CORS:

```bash
export CORS_ORIGINS='["https://fabric.example.com", "https://admin.fabric.example.com"]'
```

## Security Headers

The API returns these security-related headers on every response:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME type sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Enforce HTTPS |
| `WWW-Authenticate` | (on 401) | RFC 6750 bearer challenge |

## Rate Limiting

| Limiter | Scope | Default | Location in Middleware Stack |
|---------|-------|---------|----------------------------|
| IP-based rate limit | Per client IP | 20 req/min | Before auth (protects against unauthenticated floods) |
| Agent-based rate limit | Per agent identity | 100 req/min | After auth (enforces per-agent quota) |

## Threat Mitigations

| Threat | Mitigation |
|--------|------------|
| Token theft | Immediate revocation. Rotation with grace period. |
| Brute force login | 5 failed attempts → 15 min lock. Rate limit on `/auth/login`. |
| SQL injection | SQLAlchemy parameterized queries — no raw SQL. |
| Capability enumeration | Rate limit per agent. Audit log captures attempts. |
| Cross-team access | TenantMiddleware enforces `team_namespace` on every DB query. |
| Audit tampering | Append-only `audit_events` table. No UPDATE or DELETE on audit rows. |
| OPA bypass | Fabric API enforces OPA evaluation — agents cannot skip. |
| Secret leakage | Agent tokens never logged. Passwords never logged. PII redaction in audit pipeline. |

## Reporting Vulnerabilities

See `SECURITY.md` in the project root. Report privately to `security@ghosal.dev`.

## Agent-Level Permission Boundary Contract (#445)

MCP standardizes the handshake but not the trust model — a tool that reads a
page and a tool that submits a form with real consequences are
indistinguishable at the permissions layer. v0.4.0 adds an agent-level
permission model that classifies tools as **read-only** vs. **destructive
(mutating)** and enforces the distinction at the request level, before the
proxy call.

### Tool Classification

Every tool is classified by name prefix using a shared, deterministic classifier
(`api/services/tool_class.py`):

| Class | Prefixes | Default |
|-------|----------|---------|
| `read_only` | `get`, `list`, `search`, `read`, `find`, `query`, `check` | — |
| `mutating`  | Everything else | Unknown tools are never assumed safe |

### Agent Read-Only Scope

An `AgentClass` can be marked `is_read_only=True` (read-scoped). When True:
- Read-only tools are **allowed** (subject to trust + resource checks).
- Mutating tools are **denied** at the request level via the OPA
  `read_only_denied` rule, regardless of server trust level.

### Enforcement Point

Enforcement happens in `RoutingService.execute()` **before** the proxy call to
the MCP server. The tool class and agent read-only flag are passed to OPA; if
`read_only_denied` is True, a `PermissionDeniedError` is raised and the tool is
never invoked.

### Audit Trail

The audit event `resource_check` now includes `tool_class` and
`agent_read_only` for every evaluated request.

### Boundary Contract for Autonomous Agents

Agents operating autonomously (no human in the loop) should be assigned to a
read-only-scoped agent class. This guarantees the agent cannot mutate state
through any tool on any server, even if a trust assignment grants access — a
docs server never shares authority with a deploy server.

## Structured Policy-Denial Feedback (#443)

When OPA denies a capability invocation, the agent previously received an
opaque tool error and would blind-retry through alternative tools/paths,
adding approval-queue noise and hiding the policy decision. v0.4.0 returns a
**structured denial** instead: a denial is a *result* — not a failure.

Every denial carries:

| Field | Meaning |
|-------|---------|
| `impact` | Always `none` (nothing changed — the call had zero side effect) |
| `reason` | The policy rule id that denied, e.g. `policy:read_only_scope` |
| `suggestion` | The next allowed step, so the agent can branch or stop |

Denial reasons:
- `policy:read_only_scope` — read-only-scoped agent tried a mutating tool.
- `policy:untrusted_write` — write on an unreviewed server.
- `policy:deny_stale_mapping` — schema digest is stale/pending review.
- `policy:resource_not_allowed` — resource dimension policy rejected the values.

The router returns `403` with `{"error": "denied", "impact", "reason",
"suggestion"}` (and an explicit `"denied": true` flag). Batch requests return
the denial inline per request instead of an opaque error. Agents should
**branch on `reason`** rather than retry the same verb, which measurably
reduces approval-queue noise.
