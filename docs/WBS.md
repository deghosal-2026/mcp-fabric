# MCP Fabric — Work Breakdown Structure

> **Status:** Active  
> **Total tasks:** 500 across 15 phases  
> **Estimated effort:** 692 hours (17 weeks)  
> **Milestones:**
> - [v0.1.0 — Core Platform](https://github.com/deghosal-2026/mcp-fabric/milestone/1) (shipped)
> - [v0.3.0 — Security Hardening & Compliance](https://github.com/deghosal-2026/mcp-fabric/milestone/2) (in progress)
> **Based on:** `docs/PRD.md`, `docs/spec.md`, `docs/DESIGN.md`, `docs/ARCHITECTURE.md`

> **Issues:** v0.1.0 tasks were created under milestone [v0.1.0 — Core Platform](https://github.com/deghosal-2026/mcp-fabric/milestone/1) (368 issues, shipped). v0.3.0 tasks tracked via milestone issues on GitHub under [v0.3.0 milestones](https://github.com/deghosal-2026/mcp-fabric/milestones?state=open). Each task in phase files below links to its issue.

## Phase Index

| Phase | File | Tasks | Est. Hours | Description |
|---|---|---|---|---|
| [0](wbs/phase-0-scaffolding.md) | Scaffolding | 16 | 32h | Poetry, Makefile, Dockerfiles, Compose, Config, Main, Dependencies, Alembic, OPA, CI/CD, Repo Docs |
| [1](wbs/phase-1-database.md) | Database & Models | 82 | 60h | 17 ORM models, 20+ Pydantic schema groups, migrations, model validation |
| [2](wbs/phase-2-mcp-client.md) | MCP Client | 12 | 12h | ✅ MCPClient: list_tools, call_tool, diff_tools, timeout/retry, connection pooling |
| [3](wbs/phase-3-services.md) | Core Services | 95 | 72h | 9 services: Registry, Capability, Policy, Routing, Audit, Approval, Pack, Alert, Auth |
| [4](wbs/phase-4-middleware.md) | Middleware | 8 | 16h | RequestID, Tracing, Auth, Tenant, RateLimit, Audit, CORS, API Version |
| [5](wbs/phase-5-api-routes.md) | API Routes | 55 | 40h | 11 route groups: Registry, Capability, Routing, Policy, Approval, Audit, Pack, Auth, Admin, Health, Webhooks |
| [6](wbs/phase-6-celery.md) | Celery Tasks | 18 | 16h | Health checks, notifications, exports, thresholds, cleanup, webhook delivery |
| [7](wbs/phase-7-telemetry.md) | Telemetry | 15 | 16h | Prometheus metrics, OpenTelemetry traces, structlog, Grafana dashboard, Alertmanager rules |
| [8](wbs/phase-8-errors.md) | Error Handling | 8 | 8h | ✅ Error infrastructure, 14 error catalog entries, graceful degradation |
| [9](wbs/phase-9-admin-ui.md) | Admin UI | 85 | 64h | ✅ 16 components: Pages (12), Shared components, Login, Dashboard, Servers, Capabilities, etc. |
| [10](wbs/phase-10-testing.md) | Testing | 40 | 50h | Unit (15), Integration (8), OPA, UI (5), E2E (3), Infrastructure (6) |
| [11](wbs/phase-11-cicd.md) | CI/CD | 12 | 8h | CI pipeline, Release pipeline, Release checklist |
| [12](wbs/phase-12-docs.md) | Documentation | 27 | 16h | Code docs, Operator docs, API reference, Deployment guide |
| [OSS](wbs/phase-oss-prep.md) | Open Source Preparation | 10 | 12h | Community profile, README badges, governance, release automation, docs site, security scanning, health files |
| [13](wbs/phase-13-resource-policy.md) | Resource-Aware Policy | 12 | 184h | DB schema (4 tables), OPA Rego rules, API endpoints (dimensions + bindings), routing service resource validation, Admin UI (3 tabs + approval mismatch), audit logging, integration/E2E tests, developer guide, doc updates, release |
| [14](wbs/phase-14-v030.md) | v0.3.0 — Security Hardening & Compliance | 12 | 200h | 4 milestones: Docs & Tests, Audit & Observability, UI Safety Signals, Schema-Digest Mappings. See milestone issues for tracking. |

## Task Format

Each task in phase files follows this structure:

```markdown
### PX-NN: Task Title

**Description:** 1-2 sentences on what this task builds.
**Dependencies:** PX-NN, PY-NN
**Effort:** Xh

**Checklist:**
- [ ] Detailed checklist item 1
- [ ] Detailed checklist item 2

**Success Criteria:**
- Measurable outcome 1
- Measurable outcome 2
```

## Dependency Graph (Critical Path)

```
P0 (Scaffolding) ──► P1 (Database) ──► P2 (MCP Client) ──► P3 (Services) ──► P5 (Routes)
                          │                                                        │
                          └──► P4 (Middleware) ────────────────────────────────────┘
                                                                                    │
                          P6 (Celery) ──► P7 (Telemetry) ──► P8 (Errors) ◄────────┘
                                                                                    │
                          P9 (Admin UI) ──────────────────────────────────────────┘
                                                                                    │
P10 (Testing) ─── runs alongside P1-P9 ─────────────────┘
                            OSS (OSS Prep) ── runs alongside all phases ───────────┘
                                                                                    │
                           P11 (CI/CD) ──► P12 (Docs) ──► v0.1.0 Release ────────────┘

v0.1.0 ──► P13 (Resource-Aware Policy / v0.2.0) ──► P14 (v0.3.0 Security Hardening)

P14 phases:
  M1 (Docs & Tests) ──► M2 (Audit) ──► M3 (UI Safety)
  M4 (Schema-Digest) ── runs in parallel with M1-M3 ──► v0.3.0 Release
```

## Tracking

Status indicators per task:
- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete
- `[!]` Blocked

All tasks linked to GitHub issues. See each phase file for issue numbers.
