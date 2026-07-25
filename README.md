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
# Clone and start the full stack
git clone https://github.com/deghosal-2026/mcp-fabric.git
cd mcp-fabric
docker-compose up -d

# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# Admin UI: http://localhost:3000 (cd ui && npm run dev)
```

Or run locally without Docker:

```bash
poetry install
cd ui && npm install && cd ..
poetry run uvicorn api.main:app --reload &
cd ui && npm run dev
```

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

## Quick Start

```bash
# Install dependencies
poetry install

# Run database migrations
alembic upgrade head

# Start the API server (development)
uvicorn api.main:app --reload

# Or run the full stack with Docker Compose (API, Postgres, Redis, Celery worker/beat)
docker-compose up --build

# Run tests
poetry run pytest tests/ -v
```

The API will be available at `http://localhost:8000`. Health check: `GET /health`. Metrics: `GET /v1/metrics`.

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
