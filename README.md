# MCP Fabric

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

*Coming soon.*

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

## Who It's For

- **Platform teams** managing multiple MCP servers
- **Advanced agent builders** who need governed tool access
- **Developer experience teams** building internal AI tooling platforms
- **OSS builders** creating reusable MCP ecosystems

## License

MIT
