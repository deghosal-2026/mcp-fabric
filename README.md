# MCP Fabric

[![CI](https://github.com/deghosal-2026/mcp-fabric/actions/workflows/ci.yml/badge.svg)](https://github.com/deghosal-2026/mcp-fabric/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000)](https://github.com/astral-sh/ruff)
[![Type checked](https://img.shields.io/badge/mypy-strict-blue)](https://github.com/python/mypy)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

A control plane for AI agents — register MCP servers, normalize tools into capabilities, control access with policies and trust levels, require human approval for sensitive actions, and audit everything.

MCP solves one important problem: a standard interface for AI tools and data. It does not solve the next problem that appears immediately after success: **tool ecosystem sprawl**.

MCP Fabric is that missing layer — the dashboard where platform teams connect, organize, control, review, and monitor every tool their agents use.

## The Problem

Once a team adds multiple MCP servers, several hard questions emerge:

- Which tools should be exposed to which agents?
- How should overlapping capabilities be described?
- What trust level should be assigned to each server?
- Which agents get access to which tools — and who needs to approve?
- How should a platform team audit and govern usage across the whole tool ecosystem?

## Quick Start

```bash
# Clone and start the full stack (Docker)
git clone https://github.com/deghosal-2026/mcp-fabric.git
cd mcp-fabric
docker-compose up -d

# Or run locally without Docker:
poetry install && cd ui && npm install && cd ..
poetry run uvicorn api.main:app --reload &
cd ui && npm run dev
```

| Service | URL |
|---|---|
| API | `http://localhost:8000` |
| API Docs (Swagger) | `http://localhost:8000/docs` |
| Admin UI | `http://localhost:3000` |
| Metrics | `http://localhost:8000/v1/metrics` |
| Health | `http://localhost:8000/health` |

## Documentation

| Guide | Description |
|---|---|
| 👤 [Admin UI User Guide](docs/user-guide.md) | Walkthrough of all UI pages with screenshots |
| 📄 [Product Requirements (PRD)](docs/PRD.md) | 29 user journeys, persona definitions, product scope |
| 📐 [Technical Specification](docs/spec.md) | Full architecture, DB schema, API contract, OPA policies |
| 🏗️ [Architecture](docs/ARCHITECTURE.md) | System design, data flow, component interfaces |
| 🧪 [UI Test Plan](docs/ui-test/PLAN.md) | UI test strategy: 145 vitest tests |
| 🧪 [Docker Test Plan](docs/docker-test/PLAN.md) | E2E test strategy: Playwright + curl + 19 screenshots |
| 🛠️ [Development Guide](docs/guides/development.md) | Local setup, testing, migrations, Docker Compose |
| 🚀 [Deployment Guide](docs/guides/deployment.md) | Docker Compose deploy, env vars, backup/restore, blue-green upgrade |
| ⚙️ [Configuration Reference](docs/guides/configuration.md) | All 25 env vars with defaults, feature flags, production checklist |
| 📊 [Monitoring Guide](docs/guides/monitoring.md) | Prometheus metrics, Grafana dashboard, Alertmanager, OTel tracing |
| 🔒 [Security Guide](docs/guides/security.md) | Auth model, password policy, MFA, token lifecycle, RBAC, audit |
| ❓ [Troubleshooting Guide](docs/guides/troubleshooting.md) | Common issues: API, health checks, OPA, Redis, CORS, DB migrations |
| 📝 [Changelog](docs/CHANGELOG.md) | Version history and release notes |

## What MCP Fabric Does

MCP Fabric is a **control plane for AI agents**. It sits between your MCP servers and the agents that consume them, giving platform teams a single dashboard to manage the full lifecycle:

```
1. Register servers → 2. Define capabilities → 3. Set policies
→ 4. Create agent classes + tokens → 5. Bundle into packs
→ 6. Assign packs → 7. Approve gated actions → 8. Audit everything
```

| Layer | What It Provides |
|---|---|
| **Server Registry** | Register, inspect, and monitor MCP servers. Auto-discover tools from `/tools/list`. Filter by health, trust, team. |
| **Capability Catalog** | Normalize raw MCP tools into meaningful capabilities (e.g. `deployment:promote`). Deprecate with configurable grace periods. |
| **OPA Policy Engine** | Deploy Rego policies that govern access decisions — trust hierarchy, agent class requirements, namespace isolation. |
| **Agent Classes + Tokens** | Define agent types (`agent:developer`) and issue identity tokens (`fcp_****`). Token shown once at creation. |
| **Capability Packs** | Bundle capabilities and assign them to agent classes. Control which capabilities each class can access. |
| **Approvals** | Human-in-the-loop for sensitive capabilities. Review requests with full context (agent, capability, server, parameters). |
| **Audit Log** | Immutable record of every action — capability requests, policy changes, server events. Export for compliance (SOC2, SOX). |
| **Alerts** | Surface operational issues: server degradation, unreachable servers, unreviewed servers, denial spikes. |
| **Trust Posture** | Per-agent-class trust levels with color-coded cards. Optimistic UI updates with automatic rollback on error. |
| **Admin User Management** | RBAC with Admin/Editor/Viewer roles. MFA enforcement. |

## Architecture

```
Agent → MCP Fabric API → Registry → OPA Policy → Approval Gate → Target MCP Server
                            ↓
                      Audit Pipeline
                            ↓
                     ┌──────────────┐
                     │  Admin UI    │
                     │  (Dashboard, │
                     │   Config,    │
                     │   Monitor)   │
                     └──────────────┘
```

The Admin UI is the control plane. Platform teams use it to register servers, define capabilities, set policies, manage agent classes, bundle packs, review approvals, monitor alerts, and audit activity — all from a single dashboard.

## Stack

- **API:** FastAPI
- **Metadata store:** PostgreSQL
- **Cache:** Redis
- **Policy engine:** OPA (Open Policy Agent) Rego policies
- **Telemetry:** OpenTelemetry, Tempo, Prometheus, Grafana
- **UI:** React
- **Local dev:** Docker Compose

Everything runs locally. No enterprise dependencies required.

## Roadmap

**v0.1.0 — Current:**
- MCP server registry with auto-discovery of tools
- Normalized capability catalog with deprecation lifecycle
- OPA Rego policy engine for access decisions
- Agent classes with identity token management
- Capability packs — bundle and assign to agent classes
- Human-in-the-loop approvals for gated capabilities
- Audit log with event filtering and JSON export
- Trust posture dashboard with per-class trust levels
- Operational alerts for server health and security issues
- Admin user management with RBAC (Admin/Editor/Viewer) and MFA
- Dashboard with stat cards and recent activity panels
- 474 automated tests (backend, UI, OPA, E2E)

**v0.2.0 — Planned:**
- Advanced routing engine (health/latency/fallback-aware)
- Conflict detection across similar tools
- Capability-to-tool mapping UI from the catalog

**v0.3.0 — Planned:**
- Multi-tenant scopes and namespace isolation
- Analytics and usage heatmaps
- Webhook integrations for external tooling

**v0.4.0 — Planned:**
- Performance benchmarks and caching improvements
- Reference integrations with popular OSS MCP servers
- API versioning and SDK

## Test Status

| Suite | Tests | Status |
|---|---|---|
| Backend unit (services, middleware, errors) | 295 | ✅ Passing |
| Backend integration (HTTP routes) | 12 | ✅ Passing |
| OPA policy (Rego) | 12 | ✅ Passing |
| UI unit/integration (Vitest) | 128 | ✅ Passing |
| UI E2E + screenshots (Playwright) | 21 | ✅ Passing |
| Docker Compose E2E (curl) | 6 | ✅ Scripts ready |
| **Total** | **474** | |

```bash
make test        # Backend unit tests
make test-unit   # Unit tests only
cd ui && npm test  # UI tests
make opa-test    # OPA policy tests
```

## Who It's For

- **Platform teams** managing multiple MCP servers
- **Advanced agent builders** who need governed tool access
- **Developer experience teams** building internal AI tooling platforms
- **OSS builders** creating reusable MCP ecosystems

## License

MIT

---

See [ROADMAP](ROADMAP.md), [GOVERNANCE](GOVERNANCE.md), and [CONTRIBUTING](CONTRIBUTING.md) for project direction, governance, and how to contribute.
