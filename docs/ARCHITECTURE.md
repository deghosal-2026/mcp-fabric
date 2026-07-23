# MCP Fabric — Architecture

## Overview

MCP Fabric sits between agents and MCP servers. Agents don't connect to individual servers directly. They connect to Fabric and request capabilities. Fabric resolves which server provides that capability, enforces policy, routes the request, and returns a normalized response.

```
                    ┌──────────────┐
                    │   Agent 1    │  (incident-responder)
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │   Agent 2    │  (code-reviewer)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │              │
                    │  MCP Fabric  │
                    │              │
                    └──┬──┬──┬──┬──┘
                       │  │  │  │
              ┌────────┘  │  │  └─────────┐
              ▼           ▼  ▼            ▼
        ┌─────────┐ ┌──────────┐  ┌──────────────┐
        │ Code    │ │ Docs     │  │ Deployment   │  ...N servers
        │ Search  │ │ Server   │  │ Server       │
        └─────────┘ └──────────┘  └──────────────┘
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Admin UI                             │
│  Server Inventory │ Capability Browser │ Policy Editor     │
│  Bundle Curator  │ Audit Viewer      │ Trust Posture      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP API
┌──────────────────────────▼──────────────────────────────────┐
│                      Fabric API                             │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Registry │  │ Catalog  │  │ Routing  │  │  Policy  │   │
│  │          │  │          │  │ Engine   │  │  Layer   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │          │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐     │
│  │                  Audit Pipeline                   │     │
│  └──────────────────────┬───────────────────────────┘     │
│                         │                                  │
│  ┌──────────────────────┴───────────────────────────┐     │
│  │                  Alerting Engine                  │     │
│  └──────────────────────────────────────────────────┘     │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                  ▼
   ┌─────────┐     ┌──────────┐      ┌──────────┐
   │PostgreSQL│     │  Redis   │      │External  │
   │ (state)  │     │ (cache)  │      │MCP Srvrs │
   └─────────┘     └──────────┘      └──────────┘
```

## Component Responsibilities

### Registry
Stores the canonical state of every registered MCP server. On registration, Fabric inspects the server's `/tools/list` endpoint and stores tool definitions. Maintains health status, trust levels, ownership, labels, and version history.

**Data:** Server metadata, tool definitions, trust assignments, health status, registration history.

### Capability Catalog
Normalizes raw MCP tool definitions into a canonical capability model. A tool called `search_code` from one server and `find_in_repo` from another both map to capability `code:search`. The catalog defines the mapping, the normalized input/output schemas, and detects conflicts.

**Data:** Capability → tool mappings, normalized schemas, conflict records, deprecation status.

### Routing Engine
Resolves an incoming capability request to the best-fit MCP server. Ranking factors: capability match quality, policy compliance, latency history, and explicit routing rules (from conflict resolution). Handles fallback when a primary server fails.

**Flow:** Capability request → resolve candidates → filter by policy → rank → route → normalize response → audit.

### Policy Layer
Evaluates whether a given agent class can access a given capability from a given server. Trust levels (`trusted`, `restricted`, `approval-gated`) are assigned per server or per tool. Agent classes are mapped to allowed trust levels. Approval-gated capabilities create a pending approval record.

**Data:** Trust level assignments, agent class definitions, policy rules, approval records.

### Audit Pipeline
Captures every event: routed requests, denied requests, policy changes, server state changes, schema migrations, fallback events, and approval decisions. Provides export and retention.

**Data:** Immutable event log with typed events, timestamps, and context.

### Alerting Engine
Evaluates audit events and health check results against configurable alert rules. Triggers notifications when thresholds are crossed (health degradation, unreviewed servers, denial rate spikes, schema changes).

**Data:** Alert rules, notification channels, alert history.

### Admin UI
Web interface for managing Fabric. All operations available via the UI are also available via the API (the UI is a consumer of the API, not a bypass of it).

## Request Lifecycle

```
Agent capability request
        │
        ▼
  ┌─────────────┐
  │ 1. Identity │──► Validates agent token, resolves agent class
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │ 2. Resolve  │──► Matches requested capability against catalog
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │ 3. Policy   │──► Checks agent class against server trust levels
  └─────────────┘
        │                  ┌──────────────────┐
        ├── denied ───────►│ Log denial       │
        │                  │ Return to agent   │
        │                  └──────────────────┘
        │
        ├── approval-gated ──► Create approval record
        │                     │ Notify approver
        │                     │ Hold request
        │                     │ On approve → continue
        │                     │ On deny → log, return to agent
        │
        ▼ (approved / trusted)
  ┌─────────────┐
  │ 4. Select   │──► Chooses best server (match, policy, latency)
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │ 5. Route    │──► Proxies request to chosen MCP server
  └─────────────┘
        │                  ┌──────────────────┐
        ├── failed ───────►│ Try fallback      │
        │                  │ Log degradation   │
        │                  │ Trigger alert     │
        │                  └──────────────────┘
        │
        ▼ (success)
  ┌─────────────┐
  │ 6. Normalize│──► Maps server response to catalog output schema
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │ 7. Audit    │──► Logs: agent, capability, server, latency, outcome
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │ 8. Return   │──► Returns normalized response + routing metadata to agent
  └─────────────┘
```

## State Management

Fabric is stateful. It maintains:

| State | Storage | TTL / Retention |
|---|---|---|
| Server registry + tool definitions | PostgreSQL | Persistent |
| Capability catalog + mappings | PostgreSQL | Persistent |
| Trust levels + agent classes | PostgreSQL | Persistent |
| Policy rules | PostgreSQL | Persistent |
| Capability packs | PostgreSQL | Persistent |
| Routing rules (conflict resolution) | PostgreSQL | Persistent |
| Approval records | PostgreSQL | Persistent |
| Audit events | PostgreSQL | Configurable (default 90 days) |
| Alert history | PostgreSQL | Configurable (default 90 days) |
| Server health status + latency stats | Redis | Ephemeral (rebuilt on restart) |
| Active agent sessions | Redis | TTL-based |

## Scaling Boundaries

Fabric is designed as a single-instance control plane for v0.1.0. At scale:

- **Read-heavy:** Capability catalog, registry lookups, agent identity checks → cache in Redis.
- **Write-light:** Registry changes, policy updates, capability re-mapping are infrequent admin actions.
- **Bottleneck:** The routing engine sits in the critical path of every agent tool call. Latency matters. Routing decisions should be <50ms.

For horizontal scaling (future):
- Multiple Fabric API instances behind a load balancer, sharing PostgreSQL + Redis.
- Health checks and alert evaluations run on a single elected leader (leader election via Redis or PostgreSQL advisory locks).
- Audit pipeline scales horizontally (append-only).
