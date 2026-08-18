# Phase 15: v0.4.0 — Trust Posture, Admissions, & Review Resilience — 🚧 IN PROGRESS

> **Feature:** Pack cohesion + adversarial fuzz, agent-level permissions, structured denial feedback,
> fail-closed re-inspection, external staleness watchdog, queue prioritization, HITL approval fatigue
> **Tasks:** 9 issue-driven features across 4 milestones + mandatory engineering/release checklist
> **Dependencies:** v0.3.0 (shipped)
> **Target version:** v0.4.0
> **Branch:** `release/0.4.0`
>
> **Issue tracker:** all 9 issues are GitHub issues #439–#447 under the `[0.4.0]` prefix.
>
> **GitHub milestones:**
> - [M1 — Cohesion & Adversarial Fuzz](https://github.com/deghosal-2026/mcp-fabric/issues?q=is%3Aissue+state%3Aopen+label%3A%22%5B0.4.0%5D%22+cohesion) — ✅ done (#439, #440)
> - [M2 — Permissions & Policy Feedback](https://github.com/deghosal-2026/mcp-fabric/issues?q=is%3Aissue+state%3Aopen+label%3A%22%5B0.4.0%5D%22) — ✅ done (#445, #443, #441)
> - [M3 — Review Queue Resilience](https://github.com/deghosal-2026/mcp-fabric/issues?q=is%3Aissue+state%3Aopen+label%3A%22%5B0.4.0%5D%22) — 🚧 in progress (#444 done; #446 done; #447 backend done, UI pending)
> - [M4 — Approval Fatigue Mitigation](https://github.com/deghosal-2026/mcp-fabric/issues?q=is%3Aissue+state%3Aopen+label%3A%22%5B0.4.0%5D%22) — 🚧 pending (#442)

---

## Full Issue Index (9 / 9 0.4.0 issues)

| ID | Issue | Milestone | Status |
|----|-------|-----------|--------|
| 439 | [Trust Posture: pack cohesion score + semantic-band pack detection](https://github.com/deghosal-2026/mcp-fabric/issues/439) | M1 | [x] |
| 440 | [Nightly adversarial resource-confusion fuzz harness (lambda-clustered)](https://github.com/deghosal-2026/mcp-fabric/issues/440) | M1 | [x] |
| 445 | [Agent-level permissions: read-only vs destructive tool classification and enforcement](https://github.com/deghosal-2026/mcp-fabric/issues/445) | M2 | [x] |
| 443 | [Structured policy-denial feedback to agents (denial = result, not failure)](https://github.com/deghosal-2026/mcp-fabric/issues/443) | M2 | [x] |
| 441 | [Detect many-to-one capability-mapping collisions + require review](https://github.com/deghosal-2026/mcp-fabric/issues/441) | M2 | [x] |
| 444 | [Fail-closed on missing schema re-inspection + stale-review age alerts](https://github.com/deghosal-2026/mcp-fabric/issues/444) | M3 | [x] |
| 446 | [Staleness watchdog must be external to the review queue system](https://github.com/deghosal-2026/mcp-fabric/issues/446) | M3 | [x] |
| 447 | [Queue prioritization: separate unreachable from genuinely changed review items](https://github.com/deghosal-2026/mcp-fabric/issues/447) | M3 | [ ] |
| 442 | [HITL approval fatigue: reversibility split + bulk approve + expiring envelopes](https://github.com/deghosal-2026/mcp-fabric/issues/442) | M4 | [ ] |

---

## Milestone M1 — Cohesion & Adversarial Fuzz (due TBD)

**Dependencies:** v0.2.0 pack breadth score (#409), v0.2.0 fuzz harness (#411).

### M1-01: Pack Cohesion Score + Semantic-Band Detection ([#439](https://github.com/deghosal-2026/mcp-fabric/issues/439))

**Files to create/edit:**
- `api/services/resource_service.py` — new `compute_pack_cohesion()` / `get_pack_cohesion()`
- `api/routers/admin.py` — new endpoint `GET /admin/trust-posture/cohesion`
- `api/schemas/admin.py` — new `PackCohesionRow` response schema
- `ui/src/components/shared/PackCohesionCard.tsx` — NEW card component
- `ui/src/pages/TrustPosture.tsx` — integrate cohesion card
- `docs/guides/pack-granularity.md` — cohesion axis documentation
- `docs/ui-test/findings/screenshots/*` — updated screenshots

**Description:** Add an independent **cohesion axis** to the Trust Posture dashboard, measuring similarity dispersion of resources *within* a pack (via the resource embedding already stored). Flag packs whose members form a tight semantic cluster (a semantic band), because a tight pack of 64 is far more exposed than a scattered 64 under adversarial resource confusion (catch ~0.02 vs ~0.88). Recommend per-resource identity (pack=1) for the most sensitive clusters.

**Checklist:**
- [ ] `compute_pack_cohesion()` computes similarity dispersion (variance/std-dev of pairwise embedding similarity) within a pack
- [ ] Cohesion is independent of breadth (two packs of same size separate cleanly)
- [ ] New endpoint returns `{ pack_id, pack_name, resource_count, cohesion_score, is_semantic_band }`
- [ ] `is_semantic_band` flag fires when cluster tightness crosses configured threshold
- [ ] UI: `PackCohesionCard` with risk coloring + tooltip linking to pack-granularity.md
- [ ] Guidance: flag recommends per-resource identity (pack=1) for sensitive bands
- [ ] Fixture test: two packs of size 64 (scattered vs tight semantic band) → cohesion clearly separates, band flagged
- [ ] Regression: lambda-clustered attack (high cohesion) → hint fires
- [ ] Backend unit tests (2+) + frontend component tests (2+)
- [ ] E2E mock assertion + screenshot updated
- [ ] `make lint`, `make typecheck`, `poetry run pytest tests/ -v` pass
- [ ] Code review completed

**Success Criteria:**
- ✅ Cohesion axis present and independent of breadth
- ✅ Semantic-band packs flagged on dashboard with recommendation
- ✅ Fixture + regression tests prove separation
- ✅ All lint/typecheck/tests pass; code review done

---

### M1-02: Nightly Adversarial Resource-Confusion Fuzz Harness (λ-clustered) ([#440](https://github.com/deghosal-2026/mcp-fabric/issues/440))

**Files to create/edit:**
- `tests/security/test_adversarial_confusion_fuzz.py` — NEW λ-clustered harness
- `.github/workflows/nightly.yml` — add λ-clustered job (extend #411 nightly)
- `docs/guides/security-testing.md` — document λ parameter + interpretation

**Description:** Add a **nightly adversarial resource-confusion fuzz harness** modeling λ-clustered (semantically targeted) redirects against real pack layouts. λ=∞ (uniform) baseline matches the existing closed-form catch rate; λ=1 (tight cluster) models a similarity-targeting attacker collapsing catch to ~0.02 on a semantic band. Emit expected-vs-actual catch and alert when pack cohesion makes catch < threshold. Reference `#439` cohesion for worst-case pack identification.

**Checklist:**
- [x] Harness runs redirected-resource simulations over the λ spectrum (∞→1) against actual identity packs
- [x] λ=∞ uniform baseline matches the closed-form `catch = 1 − (P−1)/(R−1)`
- [x] λ=1 tight-cluster reproduces near-zero catch on semantic bands
- [x] Emits expected-vs-actual catch rate with structured JSON report (consistent with #411 format)
- [x] Alert when pack cohesion causes catch < configured threshold
- [x] Nightly CI job (independent of PR-gate), deterministic seeds (consistent with #411)
- [x] Unit test: harness output matches known adversary results
- [x] Nightly run on seeded packs: uniform baseline matches formula; intentionally semantic-band pack triggers warning
- [x] `docs/guides/security-testing.md` updated (λ semantics, how to run/read)
- [ ] Code review completed

**Success Criteria:**
- ✅ λ-clustered catch collapse reproduced and detected
- ✅ Uniform baseline still matches closed form (no regression)
- ✅ Nightly CI alerts on cohesion-driven low catch
- ✅ Deterministic, separated from PR-gate CI, unit-tested

---

### Milestone M1 Closeout (required to ship M1)

- [ ] **Code review** — `/review` run on full M1 diff; all high-confidence findings resolved
- [ ] **Lint clean** — `make lint` passes
- [ ] **Tests** — `poetry run pytest tests/ -v` passes, coverage **≥90%** on new code
- [ ] **Integration tests** — integration suite passes (test DB)
- [ ] **Docker tests** — `docker-compose.test.yml` integration/E2E pass
- [ ] **UI tests** — `cd ui && npm run lint && npm run typecheck && npx vitest run` + Playwright mock pass
- [ ] **Update WBS** — `docs/wbs/0.4.0/phase-15-v040.md` M1 tasks marked done
- [ ] **Close GitHub issues** — #439, #440 marked closed (with linked PRs)

---

## Milestone M2 — Permissions & Policy Feedback (due TBD)

**Dependencies:** v0.3.0 OPA `untrusted_write`/`raw_context` rules (#414), M3-02 collision review flow.

### M2-01: Agent-Level Permissions — Read-Only vs Destructive Tool Classification ([#445](https://github.com/deghosal-2026/mcp-fabric/issues/445))

**Files to create/edit:**
- `api/models/` — `tool_class` metadata (read_only / mutating) on mappings/tools
- `api/services/policy_service.py` — enforce tool-class at request level
- `api/schemas/` — tool-class in agent trust/permission schemas
- `api/routers/` — read-only permission scoping endpoint(s)
- `policies/fabric/policy.rego` + `policy_test.rego` — read-only/mutating rules
- `api/services/audit_service.py` — tool-class in audit trail
- `docs/guides/security.md` — boundary contract for agents

**Description:** Add an agent-level permissions model that classifies tools as **read-only vs destructive/mutating** and enforces the distinction at the protocol/permission layer (not just docs). Read-only tools allowed for read-scoped agents; mutating tools gated by trust + approval policy. Enforce before the proxy and surface in the audit trail. Document the boundary contract for autonomous agents.

**Checklist:**
- [x] `tool_class` (read_only / mutating) inferred or declared on mappings
- [x] Read-only agents can call read-only tools; mutating call denied (403/denial)
- [x] Writes never auto-allow without approval for read-scoped agents
- [x] Enforcement happens at request level before proxy
- [x] Tool-class captured in audit trail
- [x] OPA rules + Rego tests added (read-only pass, write blocked, trusted write allowed)
- [x] Boundary contract documented for agents (denial = structured feedback, see #443)
- [x] Backend unit + integration tests
- [ ] `make lint`, `make typecheck`, `poetry run pytest tests/ -v` pass
- [ ] Code review completed

**Success Criteria:**
- ✅ Read-scoped agent denied on mutating tools, reads pass
- ✅ Enforcement at protocol/request level, not docs-only
- ✅ Tool-class in audit trail + OPA, boundary documented
- ✅ Tests + lint/typecheck pass; code review done

---

### M2-02: Structured Policy-Denial Feedback to Agents ([#443](https://github.com/deghosal-2026/mcp-fabric/issues/443))

**Files to create/edit:**
- `api/schemas/common.py` — new `DenialResult` schema
- `api/services/policy_service.py` — build `DenialResult` on deny
- `api/routers/routing.py` or MCP proxy — return denial over tool-result channel with explicit "denied" type
- `api/services/audit_service.py` — denial recorded in audit trail
- `docs/guides/security.md` — agent boundary-feedback doc

**Description:** Return **structured policy-denial feedback** — a denial is a *result* with an impact statement (`impact: none`), a short reason (policy/rule id), and the next allowed step/capability — not an opaque tool failure. Returned over the MCP tool-result channel with an explicit "denied" type so agents can branch instead of blind-retrying.

**Checklist:**
- [x] `DenialResult` schema: `{ impact: none, reason: <rule id>, suggestion: <next allowed step> }`
- [x] Denials returned over tool-result channel with explicit "denied" type
- [x] Agent can branch on the denial result
- [x] Denial recorded in audit trail
- [ ] Optional: live agent boundary-feedback doc surfaced
- [x] Test: deny `deployment:promote`→prod → agent receives reason + next step, doesn't retry same verb
- [x] Test: blind-retry count drops vs opaque-error control
- [x] `make lint`, `make typecheck`, `poetry run pytest tests/ -v` pass
- [ ] Code review completed

**Success Criteria:**
- ✅ Denial is a structured, branchable result (not an opaque failure)
- ✅ Reason includes rule id + next allowed step
- ✅ Blind-retry count measurably reduced
- ✅ Audit trail contains structured denial; tests + quality gates pass

---

### M2-03: Detect Many-to-One Capability-Mapping Collisions + Require Review ([#441](https://github.com/deghosal-2026/mcp-fabric/issues/441))

**Files to create/edit:**
- `api/services/capability_service.py` — collision detection at mapping time
- `api/models/server.py` — collision state on mappings (extends #414 status)
- `api/routers/admin.py` — `GET /admin/capabilities/{id}/collisions` (or similar) + admin review list
- `api/schemas/capability.py` — collision response schemas
- `api/services/policy_service.py` — pass immutable raw call context (server/tool identity + args) to OPA
- `policies/fabric/policy.rego` + `policy_test.rego` — origin-aware denial
- `ui/src/pages/Reviews.tsx` — collisions section/badge
- `tests/security/` — confused-deputy fuzz case (low-trust server presenting high-trust capability name)

**Description:** Detect **many-to-one capability-mapping collisions** (multiple distinct tools mapped to the same normalized capability) and require explicit review/approval before any colliding mapping becomes routable. Pass immutable raw call context (server/tool identity + args) to OPA alongside the normalized capability so a policy can still distinguish origin. Add a confused-deputy fuzz case.

**Checklist:**
- [x] Collision detected when ≥2 distinct tools map to the same capability
- [x] Colliding mappings require explicit review before routable (blocked until approved)
- [x] Admin UI surfaces collision list (extend Reviews page) with distinct visual treatment
- [x] OPA receives raw call context (server identity + tool + args) to distinguish origin
- [x] OPA can deny based on origin (low-trust server presenting high-trust capability name)
- [x] Confused-deputy fuzz case added (per #440 harness or unit)
- [x] Register `/promote` + `/promoteDeploy` → collision surfaced, routing blocked until review
- [x] `make lint`, `make typecheck`, `poetry run pytest tests/ -v` pass
- [ ] Code review completed

**Success Criteria:**
- ✅ Many-to-one collisions detected at mapping time and gated
- ✅ Raw origin context reaches OPA for origin-based denial
- ✅ Admin review required before collision routable
- ✅ Confused-deputy case tested; quality gates pass

---

### Milestone M2 Closeout (required to ship M2)

- [ ] **Code review** — `/review` run on full M2 diff; all high-confidence findings resolved
- [ ] **Lint clean** — `make lint` passes
- [ ] **Tests** — `poetry run pytest tests/ -v` passes, coverage **≥90%** on new code
- [ ] **Integration tests** — integration suite passes (test DB)
- [ ] **Docker tests** — `docker-compose.test.yml` integration/E2E pass
- [ ] **UI tests** — `cd ui && npm run lint && npm run typecheck && npx vitest run` + Playwright mock pass
- [ ] **Update WBS** — `docs/wbs/0.4.0/phase-15-v040.md` M2 tasks marked done
- [ ] **Close GitHub issues** — #445, #443, #441 marked closed (with linked PRs)

---

## Milestone M3 — Review Queue Resilience (due TBD)

**Dependencies:** M2-03 (review flow), v0.3.0 schema-digest (#414). Tasks M3-01/02/03 evolve the same schema-digest review lifecycle and should be delivered together.

### M3-01: Fail-Closed on Missing Schema Re-Inspection + Stale-Review Age Alerts ([#444](https://github.com/deghosal-2026/mcp-fabric/issues/444))

**Files to create/edit:**
- `api/services/registry_service.py` — re-inspection failure → `stale-unverified` (fail-closed)
- `api/models/server.py` — `stale-unverified` status, `pending_since`/deadline columns
- `api/services/` — age/deadline computation on pending reviews
- `api/routers/admin.py` — deadline alert surface
- `monitoring/` — alert rule for stale-review age
- `ui/src/pages/Reviews.tsx` — show limbo/deadline state

**Description:** Guarantee **fail-closed on failed schema re-inspection** — a timeout/unreachable server marks mappings `stale-unverified` (excluded from routing) with retry/backoff, never `unchanged`. Add **age/deadline to every pending review** and alert loudly (email/dashboard) when an item outlives the threshold. Track a third state explicitly: live / retired / **limbo** (visible and time-boxed).

**Checklist:**
- [x] Re-inspection failure/timeout → mapping becomes `stale-unverified`, excluded from routing
- [x] Retry/backoff, NOT treated as `unchanged`
- [x] `pending_since`/deadline on every pending review
- [x] Un-cleared pending item triggers deadline alert (email/dashboard)
- [x] Third state tracked explicitly: live / retired / limbo (visible + time-boxed)
- [x] Renewed inspection restores mapping or creates review
- [x] Test: kill server / network timeout → mappings become `stale-unverified`, excluded
- [x] Test: un-cleared pending item triggers deadline alert
- [x] `make lint`, `make typecheck`, `poetry run pytest tests/ -v` pass
- [ ] Code review completed

**Success Criteria:**
- ✅ Fail-closed on unreachable re-inspection (never fails open)
- ✅ Pending reviews have a clock; over-threshold items alert loudly
- ✅ Limbo state explicit and time-boxed
- ✅ Tests + quality gates pass

---

### M3-02: Staleness Watchdog External to the Review Queue System ([#446](https://github.com/deghosal-2026/mcp-fabric/issues/446))

**Files to create/edit:**
- `scripts/` or `monitoring/` — NEW standalone staleness watchdog process/service
- `.github/workflows/` or `docker-compose` — separate deployment unit (sidecar / separate cron context)
- `docs/guides/monitoring.md` — watchdog architecture doc
- `monitoring/` — heartbeat + dead-man-switch alert rules

**Description:** Ensure the staleness monitoring/alerting mechanism is **architecturally external** to the review-queue system — an independent process/service whose liveness does not depend on the queue it watches. The watchdog only needs read access to item timestamps (or a dedicated staleness table) and a notification channel; it never writes to the queue. It exposes its own **heartbeat**, and a **dead-man switch** raises a human-visible alert if the watchdog itself stops checking in.

**Checklist:**
- [x] Watchdog runs as independent process/service (sidecar, separate cron context, or external checker)
- [x] Never shares the queue's process/container/service liveness
- [x] Read-only interface to item timestamps / dedicated staleness table; never writes to queue
- [x] Notifies via alert/dashboard/webhook
- [x] Watchdog exposes own heartbeat
- [x] Dead-man switch: missing N check-ins → human-visible alert immediately
- [x] Test: kill the review-queue service entirely → stale items still trigger alerts (watchdog alive & independent)
- [x] Architecture documented in monitoring guide
- [ ] Code review completed

**Success Criteria:**
- ✅ Queue failure does not silence the staleness alarm (architecturally separated)
- ✅ Watchdog heartbeat + dead-man switch present
- ✅ Kill-queue test proves independent liveness
- ✅ Documented; code review done

---

### M3-03: Queue Prioritization — Separate Unreachable from Genuinely Changed ([#447](https://github.com/deghosal-2026/mcp-fabric/issues/447))

**Files to create/edit:**
- `api/models/server.py` — `failure_class` field on review items (`unreachable` / `drifted` / `schema_mismatch` / `timeout`)
- `api/services/` — re-inspection handler writes `failure_class` when creating review item
- `api/routers/admin.py` — queue filter by class, batch retire action
- `ui/src/pages/Reviews.tsx` — separate section/visual treatment for unreachable; filter + bulk actions
- `api/services/` — grouped/prioritized notifications, auto-retire after N consecutive failures

**Description:** Distinguish **"server unreachable"** from **"schema genuinely changed"** as distinct failure classes in the review queue so items can be prioritised and routed to different responses. Unreachable = decide retire-or-wait (hands-off); drifted = review and re-approve (hands-on). Unreachable items must not bury real schema changes, and should batch into grouped notifications without counting toward the reviewer's pending-critical tally.

**Checklist:**
- [x] Every review item carries a `failure_class` (`unreachable` / `drifted` / `schema_mismatch` / `timeout`)
- [x] Re-inspection handler writes `failure_class` at item creation
- [ ] UI separates unreachable items (distinct section/visual) with filter
- [ ] Bulk action: "retire all unreachable" without per-item review
- [ ] Grouped notifications (unreachable ≠ drift); unreachable excluded from critical tally
- [ ] Optional auto-retire after N consecutive unreachable inspections
- [x] Queue of 50 unreachable + 2 changes → real changes rise to top
- [x] Backend: queue filter (`GET /mappings/stale?failure_class=`), summary (`GET /mappings/summary`), bulk retire (`POST /mappings/retire`)
- [x] `make lint`, `make typecheck`, `poetry run pytest tests/ -v` pass
- [ ] Code review completed

**Success Criteria:**
- ✅ Unreachable vs drifted are distinct, separately actionable classes
- ✅ Real schema changes not buried by unreachable noise
- ✅ Bulk retire + grouped notifications work; quality gates pass

---

### Milestone M3 Closeout (required to ship M3)

- [ ] **Code review** — `/review` run on full M3 diff; all high-confidence findings resolved
- [ ] **Lint clean** — `make lint` passes
- [ ] **Tests** — `poetry run pytest tests/ -v` passes, coverage **≥90%** on new code
- [ ] **Integration tests** — integration suite passes (test DB)
- [ ] **Docker tests** — `docker-compose.test.yml` integration/E2E pass
- [ ] **UI tests** — `cd ui && npm run lint && npm run typecheck && npx vitest run` + Playwright mock pass
- [ ] **Update WBS** — `docs/wbs/0.4.0/phase-15-v040.md` M3 tasks marked done
- [ ] **Close GitHub issues** — #444, #446, #447 marked closed (with linked PRs)

---

## Milestone M4 — HITL Approval Fatigue Mitigation (due TBD)

**Dependencies:** #443 structured feedback (denials keep prompts rare), M3 status model.

### M4-01: Reversibility Split + Bulk Approve + Expiring Envelopes ([#442](https://github.com/deghosal-2026/mcp-fabric/issues/442))

**Files to create/edit:**
- `api/services/approval_service.py` — reversibility classification, envelope budget logic, deterministic validator
- `api/models/` — `approval_envelope` model (scope, expiry, budget)
- `api/routers/approvals.py` — envelope grant + validation endpoints
- `api/schemas/approval.py` — envelope + bulk-approve schemas
- `api/services/policy_service.py` — envelope burn-down + out-of-envelope escalation
- `ui/src/pages/Approvals.tsx` — bulk-approve UI, grouping, anomaly markers, envelope status
- `tests/` — workload + escalation tests

**Description:** Reduce approval fatigue: **reversibility-based auto-approval** (reads/undo-able actions auto-approved; writes/leaving-the-system prompted), **bulk-approve** grouping with explicit anomaly markers, and **scoped expiring approval envelopes** (human grants a budget, e.g., 10 promotes to staging within the hour; deterministic validator burns it down; only out-of-envelope actions escalate).

**Checklist:**
- [ ] Actions classified by reversibility; reads/undo-able auto-approved; writes/escapes prompted
- [ ] Envelope model: scope + expiry + budget, granted by human
- [ ] Deterministic validator burns down envelope budget
- [ ] Out-of-envelope actions (new env, schema change, over-budget) always escalate
- [ ] Bulk-approve UI with explicit grouping + visible anomaly markers
- [ ] First-time-to-new-env action escalates despite envelope
- [ ] Test: 50-action workload → prompt count is small subset matching envelope+reversibility model
- [ ] Test: over-budget/new-env/schema-change always escalates
- [ ] `make lint`, `make typecheck`, `poetry run pytest tests/ -v` pass
- [ ] Code review completed

**Success Criteria:**
- ✅ Prompt count reduced to genuine anomalies (reversibility + envelope model)
- ✅ Reads/undo-able auto-approved; destructive/escape actions prompted
- ✅ Envelopes expiring + scoped; out-of-envelope always escalates
- ✅ Bulk-approve with anomaly markers; tests + quality gates pass

---

### Milestone M4 Closeout (required to ship M4)

- [ ] **Code review** — `/review` run on full M4 diff; all high-confidence findings resolved
- [ ] **Lint clean** — `make lint` passes
- [ ] **Tests** — `poetry run pytest tests/ -v` passes, coverage **≥90%** on new code
- [ ] **Integration tests** — integration suite passes (test DB)
- [ ] **Docker tests** — `docker-compose.test.yml` integration/E2E pass
- [ ] **UI tests** — `cd ui && npm run lint && npm run typecheck && npx vitest run` + Playwright mock pass
- [ ] **Update WBS** — `docs/wbs/0.4.0/phase-15-v040.md` M4 tasks marked done
- [ ] **Close GitHub issues** — #442 marked closed (with linked PR)

---

## Mandatory Engineering & Release-Readiness Checklist (crosses every milestone)

These are non-negotiable gates applied to **every** 0.4.0 feature (each M* task above already lists them; this is the consolidated checklist).

### Per-Feature Quality Gates
- [ ] **Lint clean** — `make lint` (`ruff check api/ tests/ && ruff format --check api/ tests/`) passes
- [ ] **Typecheck** — `make typecheck` (`poetry run mypy api/`) passes (address all `error:` lines)
- [ ] **All tests run** — `poetry run pytest tests/ -v` — full suite green (not just changed tests)
- [ ] **OPA tests** — `opa test policies/` passes (all Rego)
- [ ] **UI lint + typecheck** — `cd ui && npm run lint && npm run typecheck`
- [ ] **UI tests** — `cd ui && npx vitest run` (+ Playwright mock/docker E2E where applicable)
- [ ] **Code review** — `/review` run on the full diff (general subagent, Deepseek V4 Pro) — structured report with confidence scores
- [ ] **Migrations** — new Alembic migrations run forward (`alembic upgrade head`) and backward (`alembic downgrade -1`) cleanly
- [ ] **Coverage** — new services ≥80% line coverage; integration tests over pure mocks

### Release Readiness (one consolidated pass before tagging v0.4.0)
- [ ] **Version bump** — `pyproject.toml` → `0.4.0`
- [ ] **CHANGELOG.md** — add `[v0.4.0]` section with all 9 features grouped (Added/Fixed/Security); fix duplicate `[Unreleased]` block
- [ ] **README.md** — update feature list, badges, install/version references if needed
- [ ] **docs/WBS.md + docs/wbs/phase-15-v040.md** — mark shipped items, update totals/milestones
- [ ] **docs/ guides** — pack-granularity (cohesion), security (boundary feedback), monitoring (watchdog), security-testing (λ) updated
- [ ] **SECURITY.md** — threat model updates (cohesion axis, fail-closed re-inspection, many-to-one collisions)
- [ ] **ROADMAP.md / PRD.md** — reflect 0.4.0 shipped scope
- [ ] **Release workflow verification** — Docker image (`ghcr.io/deghosal-2026/mcp-fabric:0.4.0`), PyPI (`mcp-fabric-toolmesh==0.4.0`), GitHub Release — all succeed this time (0.3.0's `poetry publish` failed on empty `PYPI_TOKEN`; confirm secret is set before tagging)
- [ ] **Release tag** — `git tag -a v0.4.0 -m "v0.4.0"` + `git push origin main --tags`
- [ ] **CHANGELOG link refs** — add `[v0.4.0]:` compare/release links at bottom

---

## Build Order & Dependencies

```
M1-01 (cohesion) ──────► M1-02 (λ-clustered fuzz)     (M1 parallel-safe, independent)
                                                            │
M2-01 (read-only/destructive) ──► M2-02 (denial feedback)   │
          │                                                ▼
          └──► M2-03 (many-to-one collisions)           (M2 sequential chain, uses #443)
                                                            │
M3-01 (fail-closed + age alerts) ──► M3-02 (external watchdog)
          │                                     │
          └──► M3-03 (queue prioritization)  (M3 ordered: watchdog depends on age-alert concept)
                                                            │
M4-01 (approval fatigue) ── depends on M2-02 (denials)     │
                                                            ▼
                              Mandatory Engineering & Release-Readiness Checklist
                                                            │
                                                            ▼
                                                       v0.4.0 Release
```

- **M1** independent, parallel-safe.
- **M2** sequential: 445 → 443 → 441 (feedback builds on permission model; collisions build on origin context).
- **M3** ordered: 444 (age alerts) → 446 (external watchdog) → 447 (raw-drawn-class tags). Delivered as one lifecycle unit.
- **M4** depends on M2-02 (denial feedback reduces prompt frequency).
- **Cross-cutting:** every feature ships with lint/typecheck/tests/code review; all consolidated before release.

---

## Delivery Summary

**To be updated at release.** Track: 9 issues across 4 milestones + mandatory engineering/release checklist.

### Test Results (expected baseline at release)

| Check | Expected |
|-------|----------|
| Python tests (pytest) | All pass (new features) + 326 existing |
| Ruff lint + format | Clean (api/ tests/) |
| Mypy | Clean (pre-existing noted errors only) |
| OPA policy tests | All pass (additions: read-only, origin-aware deny) |
| UI typecheck | Clean |
| Playwright mock E2E | All pass (extended: cohesion, collisions, bulk approve) |
| Playwright Docker E2E | Screenshots updated |
