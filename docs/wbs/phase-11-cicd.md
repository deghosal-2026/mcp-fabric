# Phase 11: CI/CD

> **Tasks:** 12 · **Effort:** 8h (1 day)  
> **Dependencies:** Phase 10 (tests must pass), P0-13 (CI workflow exists)

### P11-01: CI Pipeline — Lint Jobs
**Effort:** 0.5h | **Deps:** P0-13
**Checklist:** Verify lint job: ruff check passes → ruff format --check passes → ESLint passes → Prettier passes.
**Success Criteria:** All lint jobs green. Violations fail CI.

### P11-02: CI Pipeline — Test Jobs
**Effort:** 1h | **Deps:** P0-13, Phase 10
**Checklist:** Verify test-sqlite job: runs unit tests → coverage reported → verify test-postgres job: runs integration tests → alembic upgrade head first → verify opa-tests job: opa test passes → verify typecheck job: mypy passes → verify ui-lint job: npm lint + npm typecheck passes.
**Success Criteria:** All test jobs green. Coverage >80%. No type errors.

### P11-03: CI Pipeline — Security Scan
**Effort:** 0.5h | **Deps:** P0-13
**Checklist:** pip-audit scans Python deps → npm audit --audit-level=high scans UI deps → both fail CI on high/critical vulns.
**Success Criteria:** No high/critical vulns. Warnings logged but don't fail.

### P11-04: CI Pipeline — Parallel Execution
**Effort:** 0.5h | **Deps:** P11-01 through P11-03
**Checklist:** Verify lint + opa-tests + typecheck + security-scan run in parallel → test-sqlite + test-postgres run in parallel → total CI time < 5 minutes.
**Success Criteria:** All parallelizable jobs execute simultaneously. CI feedback fast.

### P11-05: Release Workflow — Docker Build
**Effort:** 1h | **Deps:** P0-04, P0-05, P0-14
**Checklist:** Docker image builds → tagged with vX.Y.Z, vX.Y, vX, latest → pushed to ghcr.io → image size < 300MB → verify image runs and responds on /health.
**Success Criteria:** All 4 tags pushed. Image pulls and runs correctly.

### P11-06: Release Workflow — PyPI Publish
**Effort:** 0.5h | **Deps:** P0-14
**Checklist:** `poetry build` creates wheel + sdist → `poetry publish` (requires PYPI_TOKEN) → verify `pip install mcp-fabric==0.1.0` works.
**Success Criteria:** Package on PyPI. pip install succeeds.

### P11-07: Release Workflow — GitHub Release
**Effort:** 0.5h | **Deps:** P0-14
**Checklist:** Create GitHub Release with tag → attach changelog notes → link to Docker image + PyPI package.
**Success Criteria:** Release page shows changelog + download links.

### P11-08: Release Checklist — Pre-Release
**Effort:** 1h | **Deps:** P11-01 through P11-07
**Checklist:** All CI green → CHANGELOG updated → migration tested (upgrade+downgrade SQLite+PostgreSQL) → OPA tests pass → security scan passes → OpenAPI diff reviewed (no accidental breaking changes) → README Quick Start validated.
**Success Criteria:** All checks pass before tag creation.

### P11-09: Release Checklist — Post-Release
**Effort:** 0.5h | **Deps:** P11-08
**Checklist:** `docker pull ghcr.io/...:v0.1.0` + smoke test → `pip install mcp-fabric==0.1.0` + smoke test → deploy to staging → capability request works → announce in GitHub Discussions.
**Success Criteria:** Both Docker + PyPI work. Staging deployment healthy.

### P11-10: Dependabot Verification
**Effort:** 0.5h | **Deps:** P0-15
**Checklist:** Verify Dependabot opens PRs → grouped PRs reduce noise → security alerts trigger immediate PRs → auto-merge enabled for patch updates (if CI passes).
**Success Criteria:** Dependabot runs on schedule. Grouped PRs consolidate related deps.

### P11-11: CI Badge in README
**Effort:** 0.5h | **Deps:** P11-01 through P11-03
**Checklist:** Add CI status badge (from GitHub Actions) → coverage badge (from codecov) → license badge → Python version badge.
**Success Criteria:** Badges render on GitHub. CI badge shows "passing". Coverage badge shows "80%+".

### P11-12: CODEOWNERS Verification
**Effort:** 0.5h | **Deps:** P0-16
**Checklist:** Verify @deghosal-2026 auto-requested as reviewer on all PRs → CODEOWNERS file in .github/.
**Success Criteria:** PRs auto-assign reviewer. CODEOWNERS valid syntax.
