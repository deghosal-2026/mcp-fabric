# Phase 12: Documentation

> **Tasks:** 27 · **Effort:** 16h (2 days)  
> **Dependencies:** All phases (document everything built)

## 12.1 Code Documentation (8 tasks)

### P12-01: Python Docstrings — Services
**Effort:** 2h | **Deps:** Phase 3
**Checklist:** All public methods in 9 service classes have Google-style docstrings: Args, Returns, Raises → class-level docstring explaining responsibility.
**Success Criteria:** `pydocstyle api/services/` passes. IDE hover shows docs.

### P12-02: Python Docstrings — Routes
**Effort:** 2h | **Deps:** Phase 5
**Checklist:** All route handlers have docstrings: summary, description, response descriptions for each status code → OpenAPI operation_id auto-generated from function names.
**Success Criteria:** Swagger UI shows endpoint descriptions. /openapi.json includes all docstrings.

### P12-03: Python Docstrings — Models + Middleware
**Effort:** 1h | **Deps:** Phase 1, Phase 4
**Checklist:** ORM models: column-level comments explaining purpose → Pydantic schemas: Field(description=...) for all fields → middleware: class docstring explaining position in pipeline.
**Success Criteria:** All models documented. Schema fields have descriptions in OpenAPI.

### P12-04: OpenAPI Spec Accuracy
**Effort:** 1.5h | **Deps:** Phase 5
**Checklist:** Review /openapi.json: all endpoints present → all request/response schemas complete → all status codes documented → examples present for key endpoints → tags grouped correctly → no missing required fields.
**Success Criteria:** OpenAPI spec is accurate and complete. Can generate client SDK from it.

### P12-05: TypeScript Types from OpenAPI
**Effort:** 1h | **Deps:** P12-04
**Checklist:** Generate TypeScript types from OpenAPI spec (openapi-typescript) → share types between API client and UI components → verify types match actual API responses.
**Success Criteria:** UI components use generated types. Type errors caught at compile time.

### P12-06: Inline Code Comments
**Effort:** 1h | **Deps:** All phases
**Checklist:** Complex logic has explanatory comments (routing algorithm, fallback chain, OPA integration) → non-obvious decisions have "why" comments → no obvious comments (don't explain `x = x + 1`).
**Success Criteria:** New contributor can understand routing logic from code + comments.

### P12-07: README Verification
**Effort:** 0.5h | **Deps:** All phases
**Checklist:** Follow README Quick Start on fresh machine → verify all commands work → verify first request succeeds → verify badges render → verify links to docs work.
**Success Criteria:** README produces working instance. No missing steps.

### P12-08: API Reference Generation
**Effort:** 0.5h | **Deps:** P12-04
**Checklist:** Verify /docs (Swagger) renders correctly → /redoc renders → both include all endpoints, schemas, examples → interactive "Try it out" works for test endpoints.
**Success Criteria:** Swagger + ReDoc fully functional. API explorable from browser.

## 12.2 Operator Documentation (10 tasks)

### P12-09: Deployment Guide — Docker Compose
**Effort:** 1h | **Deps:** P0-06
**Checklist:** `docs/deployment/docker-compose.md` — prerequisites (Docker, Docker Compose) → clone + start → verify health → register first server → basic configuration (env vars, volumes, networks) → troubleshooting (port conflicts, DB connection, OPA).
**Success Criteria:** New operator deploys in < 20 minutes following guide.

### P12-10: Deployment Guide — Kubernetes
**Effort:** 1.5h | **Deps:** P0-04, P0-05
**Checklist:** `docs/deployment/kubernetes.md` — basic manifests: Deployment (API, UI, Celery worker, Celery beat), Service (API, UI), ConfigMap (env vars), Secret (DB password, secret key), PVC (PostgreSQL, Redis) → health probes → resource limits.
**Success Criteria:** `kubectl apply -f` deploys working Fabric. Probes keep pods healthy.

### P12-11: Configuration Reference
**Effort:** 1h | **Deps:** P0-07
**Checklist:** `docs/reference/configuration.md` — all 18 env vars documented: name, default, description, required (dev vs prod), example values → feature flags documented → Celery beat schedule documented.
**Success Criteria:** Every env var in config.py documented. Examples work.

### P12-12: API Reference
**Effort:** 1h | **Deps:** P12-04
**Checklist:** `docs/reference/api.md` — overview of auth, versioning, pagination → endpoint groups with examples → common error responses → rate limiting → webhook delivery.
**Success Criteria:** Developer can integrate Fabric API using only this reference.

### P12-13: OPA Policy Guide
**Effort:** 1h | **Deps:** P0-12, P3-17
**Checklist:** `docs/guides/opa-policies.md` — Rego primer for Fabric → default policy explanation → customizing trust levels → adding agent classes → cross-team policies → deploying bundles → testing policies.
**Success Criteria:** Platform team can write custom policies from this guide.

### P12-14: Backup and Restore Guide
**Effort:** 0.5h | **Deps:** None (v0.1.0 uses pg_dump)
**Checklist:** `docs/guides/backup-restore.md` — PostgreSQL: pg_dump + pg_restore commands → SQLite: copy fabric.db → restore procedure → verification. Note: fabric-admin CLI coming in v0.2.0.
**Success Criteria:** Operator can back up and restore Fabric state.

### P12-15: Upgrade Guide
**Effort:** 1h | **Deps:** None
**Checklist:** `docs/guides/upgrade.md` — blue-green procedure from spec Section 17 → pre-upgrade checklist → migration testing → rollback procedure → Celery worker drain-then-upgrade.
**Success Criteria:** Operator can upgrade Fabric without downtime following guide.

### P12-16: Monitoring Guide
**Effort:** 1h | **Deps:** Phase 7
**Checklist:** `docs/guides/monitoring.md` — Prometheus setup (scrape config) → import Grafana dashboard → Alertmanager rules → log aggregation (JSON to ELK/Loki) → key metrics to watch → alert response runbook.
**Success Criteria:** Operator can set up monitoring stack following guide.

### P12-17: Troubleshooting Guide
**Effort:** 1h | **Deps:** All phases
**Checklist:** `docs/guides/troubleshooting.md` — common errors + solutions: cannot connect to DB, OPA unreachable, MCP server timeout, agent token invalid, high latency, approval not routing → diagnostic commands → log analysis → escalation.
**Success Criteria:** 10+ common issues documented with solutions.

### P12-18: Security Guide
**Effort:** 0.5h | **Deps:** Phase 9 (security model)
**Checklist:** `docs/guides/security.md` — authentication overview → token management → MFA setup → password policy → audit logging → threat model summary → vulnerability reporting (link to SECURITY.md).
**Success Criteria:** Admin understands security posture from this guide.

## 12.3 Developer Documentation (5 tasks)

### P12-19: Architecture Decision Records
**Effort:** 1h | **Deps:** Design docs
**Checklist:** `docs/adr/` — 001: Use SQLite for local dev + PostgreSQL for prod → 002: Use OPA for policy engine → 003: Use Celery for background tasks → 004: Use TanStack Query for UI server state → 005: Use header-based API versioning.
**Success Criteria:** 5 ADRs document key decisions with context + consequences.

### P12-20: Contributing Guide Verification
**Effort:** 0.5h | **Deps:** P0-16
**Checklist:** Follow CONTRIBUTING.md on fresh machine → verify setup works → verify PR process documented → verify code style enforced by tools.
**Success Criteria:** New contributor can set up and contribute from guide.

### P12-21: Local Development Guide
**Effort:** 1h | **Deps:** P0-06
**Checklist:** `docs/development/local-setup.md` — prerequisites → poetry install → SQLite mode (zero Docker) → Docker Compose mode → running tests → running linters → debugging → common issues.
**Success Criteria:** Developer has working local env in < 15 minutes.

### P12-22: Testing Guide
**Effort:** 0.5h | **Deps:** Phase 10
**Checklist:** `docs/development/testing.md` — test structure → running specific test types → writing new tests → mock MCP server usage → test factories → coverage.
**Success Criteria:** Developer can write tests following guide.

### P12-23: Release Process Guide
**Effort:** 0.5h | **Deps:** Phase 11
**Checklist:** `docs/development/release.md` — semver policy → release checklist → tagging → CI triggers → post-release verification.
**Success Criteria:** Maintainer can release following guide.

## 12.4 Project Documentation (4 tasks)

### P12-24: Docs Index Page
**Effort:** 0.5h | **Deps:** P12-09 through P12-23
**Checklist:** `docs/README.md` — index of all docs: deployment, reference, guides, development, ADRs → linked from main README.
**Success Criteria:** All docs discoverable from index.

### P12-25: Changelog v0.1.0 Entry
**Effort:** 0.5h | **Deps:** All phases
**Checklist:** Update CHANGELOG.md [Unreleased] → [0.1.0] with all features: server registry, capability catalog, routing, OPA, auth, packs, multi-team, admin UI, telemetry, CI/CD.
**Success Criteria:** Changelog matches actual v0.1.0 features.

### P12-26: GitHub Issue Labels Verification
**Effort:** 0.5h | **Deps:** None
**Checklist:** Verify all labels created: phase-0 through phase-12, type:feature/infra/test/docs, priority:p0/p1/p2 → verify milestone v0.1.0 exists.
**Success Criteria:** All labels present. Milestone has due date.

### P12-27: Project Board Setup
**Effort:** 0.5h | **Deps:** P12-26
**Checklist:** Create GitHub Project board "v0.1.0" with columns: Backlog, Ready, In Progress, In Review, Done → auto-add issues with milestone v0.1.0.
**Success Criteria:** Board visible on repo. Issues auto-populate.
