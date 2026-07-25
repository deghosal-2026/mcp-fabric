# Resource-Aware Policy Enforcement — Design Doc

> **Status:** Draft  
> **Version:** 1.0  
> **Last updated:** 2026-07-25  
> **Author:** Debashish Ghosal  
> **Source:** Community feedback — Alexey Spinov on dev.to

---

## Problem

The current OPA policy evaluates `(agent_class, capability, server_trust_level, team_namespace)` — the verb only. It can answer "may agent:release-engineer use `deployment:promote`?" but not "may agent:release-engineer use `deployment:promote` on `env:prod`?"

Alexey Spinov demonstrated: verb-only OPA passes 5/5 constructed test cases where the capability is correct in every one but the environment, tenant, or service differs. 4 of 5 would leave the agent's box. The line between approving a verb and approving an action is the difference between constrained and unconstrained agent behavior.

## Solution: Dynamic Resource Dimensions (Approach C)

Instead of hardcoding resource dimensions (env, tenant, service) into the codebase, let platform teams define them per-capability at runtime. Each dimension is a key-value pair that the policy engine evaluates against identity-bound allowlists.

## Architecture

### DB Schema

Four new tables:

- `resource_dimensions` — declares what dimensions constrain a capability (e.g., `deployment:promote` is constrained by `env`, `tenant`, `service`)
- `identity_resource_bindings` — maps an agent identity to allowed values per dimension (e.g., agent X may use `env: [staging, dev]`)
- `pack_resource_bindings` — same, but inherited from a capability pack
- `capability_dimension_map` — which dimensions apply to which capability (many-to-many)

### OPA Policy Changes

The input schema gains two new fields:
- `identity_resources: { "env": ["staging", "dev"], ... }` — from identity + pack bindings
- `request_resources: { "env": "staging", ... }` — from the agent's capability request

New Rego rule:
```rego
resource_allowed {
    dims := capability_dimensions[input.capability]
    every dim in dims {
        input.identity_resources[dim][_] == input.request_resources[dim]
    }
}
```

The existing `allow` rule gains `resource_allowed` as an additional gate.

### API Changes

- `POST /admin/capabilities/{id}/dimensions` — define dimensions for a capability
- `POST /admin/agents/{identity_id}/resources` — bind resource values to agent
- `POST /admin/packs/{pack_id}/resources` — bind resource values to pack
- `POST /capability/request` gains an optional `resources` field

### Approval Integration

When a resource-gated request is held for human approval, the approval UI shows the dimension mismatch and allows the approver to approve with a pinned resource override.

## Constraints

1. Integration with existing approval workflow — resource violations can trigger approval-gated flow
2. Works with capability packs — pack-level resource bindings merge with identity-level bindings
3. Audit trail captures both identity resources and request params in the `audit_events.details` JSONB

## Tech Tradeoffs

### vs Approach A (hardcoded dimensions)

| Factor | Approach A (Hardcoded) | Approach C (Dynamic) |
|--------|----------------------|---------------------|
| Flexibility | Fixed set (env, tenant, service) | Any dimension at runtime |
| UI complexity | Low (no dimension management) | High (3 new admin pages) |
| Rego complexity | Simple (known keys) | Loops over dynamic keys |
| Migration | Trivial (seed data) | Requires dimension definition step |
| Combinatorial explosion | New env → new identity | One identity with `env: [a, b, c]` |

### vs Approach B (Python pre-processor)

| Factor | Approach B (Pre-processor) | Approach C (Dynamic) |
|--------|---------------------------|---------------------|
| Policy location | Split (Python + Rego) | Single (Rego) |
| Audit transparency | OPA doesn't see raw violation | OPA sees everything |
| Implementation effort | Low | Medium |
| Extensibility | Code change needed | Configuration change |

## Effort Estimate

| Component | Estimated Hours |
|-----------|----------------|
| DB schema + migrations | 12 |
| OPA policy changes + tests | 16 |
| API endpoints (dimensions, bindings) | 24 |
| Routing service changes (resource validation) | 8 |
| Admin UI pages (dimensions, bindings) | 40 |
| Approval UI integration (resource mismatch display) | 16 |
| Audit schema update | 4 |
| Tests (backend + E2E) | 40 |
| **Total** | **~160 hours (~4 weeks)** |

## Placement

v0.2.0 — after core routing and governance are stable in v0.1.0.
