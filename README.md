# MCP Fabric

[![CI](https://github.com/deghosal-2026/mcp-fabric/actions/workflows/ci.yml/badge.svg)](https://github.com/deghosal-2026/mcp-fabric/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000)](https://github.com/astral-sh/ruff)
[![Type checked](https://img.shields.io/badge/mypy-strict-blue)](https://github.com/python/mypy)

A composable tool mesh for MCP ecosystems — server registry, capability normalization, trust policies, capability routing, and audit for agentic tool platforms.

MCP solves one important problem: a standard interface for AI tools and data. It does not solve the next problem that appears immediately after success: **tool ecosystem sprawl**.

MCP Fabric is that missing layer.

## The Problem

Once a team adds multiple MCP servers, several hard questions emerge:

- Which tools should be exposed to which agents?
- How should overlapping capabilities be described?
- What trust level should be assigned to each server?
- How should an agent choose between several tools that look similar?
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
|---|---|---|
| 👤 [Admin UI User Guide](docs/user-guide.md) | Walkthrough of all 12 UI pages with 19 screenshots |
| 📄 [Product Requirements (PRD)](docs/PRD.md) | 29 user journeys, persona definitions, product scope |
| 📐 [Technical Specification](docs/spec.md) | Full architecture, DB schema, API contract, OPA policies |
| 🏗️ [Architecture](docs/ARCHITECTURE.md) | System design, data flow, component interfaces |
| 🧪 [Test Plan](docs/ui-test/PLAN.md) | UI test strategy: 145 vitest + 21 Playwright + 19 screenshots |
| 🛠️ [Development Guide](docs/guides/development.md) | Local setup, testing, migrations, Docker Compose |
| 🚀 [Deployment Guide](docs/guides/deployment.md) | Docker Compose deploy, env vars, backup/restore, blue-green upgrade |
| ⚙️ [Configuration Reference](docs/guides/configuration.md) | All 25 env vars with defaults, feature flags, production checklist |
| 📊 [Monitoring Guide](docs/guides/monitoring.md) | Prometheus metrics, Grafana dashboard, Alertmanager, OTel tracing |
| 🔒 [Security Guide](docs/guides/security.md) | Auth model, password policy, MFA, token lifecycle, RBAC, audit |
| ❓ [Troubleshooting Guide](docs/guides/troubleshooting.md) | Common issues: API, health checks, OPA, Redis, CORS, DB migrations |
| 📝 [Changelog](docs/CHANGELOG.md) | Version history and release notes |

## What MCP Fabric Does

MCP Fabric acts like a **service mesh for MCP**. Not replacing the protocol, but making it operable and safe in real environments.

| Layer | What It Provides |
|---|---|
| **Registry** | Server metadata, tool metadata, ownership, trust scores, health, classification |
| **Capability Catalog** | Normalize raw tools into meaningful, queryable capabilities |
| **Routing Engine** | Choose the best server/tool per request based on capability, latency, trust, policy |
| **Policy Layer** | Expose, restrict, or gate tools per agent class |
| **Audit Pipeline** | Capture routed calls, denials, fallbacks, outcomes |
| **Admin UI** | Server inventory, overlap review, trust posture, bundle curation, usage insights |

## Architecture

```
Agent → MCP Fabric → Registry → Policy → Router → Target MCP Server
                        ↓
                  Audit Pipeline
```

Agents stop thinking in terms of arbitrary server sprawl and instead receive a **coherent capability layer**.

## Stack

- **API:** FastAPI
- **Metadata store:** PostgreSQL
- **Cache:** Redis
- **Policy engine:** Python rules (optional OPA integration later)
- **Telemetry:** OpenTelemetry, Tempo, Prometheus, Grafana
- **UI:** React
- **Local dev:** Docker Compose

Everything runs locally. No enterprise dependencies required.

## Roadmap

**v0.1.0 — MVP:**
- MCP server registry with tool metadata
- Normalized capability catalog
- Policy layer for trust/exposure decisions
- Capability-based routing
- Audit logs for routed requests and denials
- Simple admin UI for inventory and trust review

**v0.2.0:**
- Bundle curation by workflow
- Conflict detection across similar tools
- Richer trust review flows

**v0.3.0:**
- Multi-tenant scopes
- Health, latency, and fallback-aware routing
- Approval-gated capability classes

**v0.4.0:**
- Analytics and usage heatmaps
- Stronger auth adapters
- Reference integrations with popular OSS MCP servers

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
