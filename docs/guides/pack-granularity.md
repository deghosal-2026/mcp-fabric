# Pack Granularity Guide

How to size capability packs so identity-binding provides meaningful protection.

## The Problem

Identity-binding (v0.2.0) constrains agents to specific resources within a capability — but only as tightly as the pack allows. A pack that covers every resource provides zero protection. A pack covering one resource provides complete protection.

This is not a bug. It is an architectural constraint: **identity-binding scope is bounded by pack breadth.** The platform engineer who authors the pack decides the protection level.

## The Formula

Alexey Spinov independently validated the closed form:

```
catch = 1 - (pack_size - 1) / (total_resources_in_domain - 1)
```

| Variable | Meaning | Example |
|---|---|---|
| `catch` | Fraction of confused-deputy attacks this pack configuration blocks | 0.8758 = 87.58% |
| `pack_size` | Number of distinct resources the pack covers | 64 resources |
| `total_resources_in_domain` | Total distinct resources across all servers in this capability domain | 512 resources |

### Intuition

- **pack_size = 1:** `catch = 1.0` — per-resource identity, full protection. An agent can only hit exactly one resource.
- **pack_size = total_resources:** `catch = 0.0` — the pack is as broad as the domain. Identity-binding adds nothing.
- **Everything between:** Linear degradation. Each additional resource in the pack linearly reduces protection.

## Catch Rate by Pack Size

These tables assume a domain of 512 resources (adjust for your actual domain size using the formula).

| Pack Size | Catch Rate | Protection |
|---|---|---|
| 1 | 100.00% | Complete |
| 2 | 99.80% | Excellent |
| 4 | 99.41% | Excellent |
| 8 | 98.63% | Excellent |
| 16 | 97.06% | Strong |
| 32 | 93.93% | Strong |
| 64 | 87.66% | Moderate |
| 128 | 75.15% | Reduced |
| 256 | 50.10% | Weak |
| 512 | 0.00% | None |

### For Different Domain Sizes

| Pack Size | Domain=128 | Domain=256 | Domain=512 | Domain=1024 |
|---|---|---|---|---|
| 1 | 100.00% | 100.00% | 100.00% | 100.00% |
| 8 | 94.49% | 97.25% | 98.63% | 99.31% |
| 16 | 88.19% | 94.12% | 97.06% | 98.53% |
| 32 | 75.59% | 87.84% | 93.93% | 96.97% |
| 64 | 50.39% | 75.29% | 87.66% | 93.84% |
| 128 | 0.00% | 50.20% | 75.15% | 87.58% |
| 256 | — | 0.00% | 50.10% | 75.05% |

## Recommended Thresholds by Risk Level

| Risk Level | Capability Examples | Max Pack Size | Min Catch Rate |
|---|---|---|---|
| **Write / Mutate** | `deployment:promote`, `database:query`, `incident:resolve` | ≤8 | ≥98% |
| **Read / Sensitive** | `code:blameless-diff`, `vulnerability:scan`, `secret:detect` | ≤32 | ≥94% |
| **Read / Standard** | `knowledge:search`, `code:search`, `dependency:list` | ≤64 | ≥87% |
| **Read / Low Sensitivity** | `docs:list`, `status:health`, `metrics:get` | ≤128 | ≥75% |

### Guidance by Capability Type

**Write capabilities** need the tightest packs because the blast radius is highest. A confused-deputy attack on `deployment:promote` could push to prod instead of staging. Keep write packs to 8 or fewer resources.

**Read capabilities on sensitive data** (vulnerability reports, secrets, PII) still have meaningful blast radius. Keep these to 32 or fewer resources.

**Read-only low-sensitivity capabilities** can tolerate broader packs. The cost of a wrong resource is inconvenience, not breach.

## Decision Tree: When to Split a Pack

```
Is the pack size within the recommended threshold for this risk level?
├── Yes → Keep pack as-is
└── No → Ask:
     ├── Can resources be grouped by environment (staging vs prod)?
     │   └── Yes → Split into env-specific packs
     ├── Can resources be grouped by tenant / team?
     │   └── Yes → Split into tenant-scoped packs
     ├── Can resources be grouped by data sensitivity?
     │   └── Yes → Split by sensitivity tier
     └── No → Split by resource ID range or alphabetical bucketing
              (last resort — prefer semantic grouping)
```

## Worked Example

**Scenario:** You have a deployment MCP server with 512 environments across staging, prod, and DR. You're creating a pack for `agent:release-engineer` that needs access to `deployment:promote`.

**Step 1 — Check recommended max:** Write capabilities → ≤8 resources.

**Step 2 — Count current pack:** If the pack includes all 512 environments, `catch = 0%`. Identity-binding does nothing.

**Step 3 — Split by environment:**
- `deployment:promote (staging)` — 4 staging environments. Pack size = 4. Catch rate = 99.41%. ✅
- `deployment:promote (prod)` — 6 production environments. Pack size = 6. Catch rate = 99.02%. ✅

**Step 4 — Assign agent to correct pack:** `agent:release-engineer` gets the staging pack. A separate `agent:deploy-master` class gets the prod pack.

**Result:** A compromised release-engineer agent cannot promote to prod — `prod` is not in its identity-bound resource set.

## Why This Matters

Without pack granularity guidance, platform engineers will create broad packs that accidentally reproduce the v0.1 verb-only hole. The identity-binding mechanism is sound — but its effectiveness depends entirely on how packs are authored.

This is a **pack authoring discipline** problem, not a runtime enforcement problem. The audit trail records `pack_resource_count` and `implied_catch_rate` at request time so compliance teams can retroactively verify protection levels.

## The Cohesion Axis (v0.4.0, #439)

The catch-rate formula assumes **uniform** intra-pack confusion — that a confused redirect lands anywhere in the pack with equal probability. That assumption breaks for **semantic bands**: packs whose members form a tight semantic cluster. A similarity-targeting attacker (the λ-clustered adversary in #440) preferentially redirects toward the pack's most similar members, collapsing the effective catch rate to ~0.02 on a tight band of 64 — versus ~0.88 for a *scattered* pack of the same size.

**Pack cohesion** measures similarity dispersion of resources *within* a pack via the stored resource embedding (variance/std-dev of pairwise embedding similarity). Cohesion is **independent of breadth**: two packs of equal size separate cleanly on the cohesion axis.

The Trust Posture dashboard surfaces this as `GET /admin/trust-posture/cohesion` with a per-pack `cohesion_score` and an `is_semantic_band` flag. A flagged semantic band is a signal to split on **semantics**, not just size:

- A semantically homogeneous pack of 64 is far more exposed than a scattered 64 under adversarial resource confusion.
- **Recommendation:** for the most sensitive semantic bands, author **per-resource identity** (pack = 1 resource) so a similarity-targeted redirect has no nearby member to land on.

Use the two axes together:

| Axis | Question | Action when exposed |
|---|---|---|
| Breadth | How many resources can the agent reach? | Narrow the pack by capability sensitivity |
| Cohesion | How similar are the resources it can reach? | Split tight semantic bands; prefer per-resource identity for high-value clusters |

## Further Reading

- [Resource-Aware Policy Design](../resource-aware-policy-design.md) — Design doc for the identity-binding mechanism
- [Adversarial Fuzz Harness](security-testing.md) — λ-clustered adversary that exploits tight semantic bands (#440)
- [PRD Journey 30](../PRD.md#journey-30-resource-constrained-policy--binding-identity-to-allowed-targets) — Resource-constrained policy user journey
- [SECURITY.md](../../SECURITY.md) — Threat model and known limitations
- Alexey Spinov's validation: https://dev.to/alex_spinov/comment/3bpa9
