# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in MCP Fabric, please report it privately. Do not open a public issue.

**Email:** security@ghosal.dev

Please include:

- A detailed description of the vulnerability
- Steps to reproduce
- The affected version(s)
- Any potential impact or exploit scenario

## Response Timeline

- **Acknowledgment:** Within 48 hours
- **Initial assessment:** Within 5 business days
- **Fix timeline:** Depends on severity — critical issues prioritized for immediate patch release

## Supported Versions

| Version | Supported |
|---|---|
| Latest (main) | :white_check_mark: |
| Older versions | :x: |

## Security Design Principles

MCP Fabric is built with the following security principles:

- **Agent identity is verified on every request.** No unauthenticated capability requests are accepted.
- **Policy enforcement is server-side.** Agents cannot bypass Fabric's trust and permission checks.
- **Approval-gated capabilities require human authorization.** Sensitive operations cannot be executed without explicit approval.
- **All access is logged.** Every capability request, denial, approval, and policy change is captured in the audit pipeline.
- **Secrets are never logged.** Agent tokens, passwords, and sensitive parameters are redacted from audit logs.
- **Token rotation is supported.** Compromised agent identities can be rotated without downtime.

## Threat Mitigations

| Threat | Mitigation |
|---|---|
| Token theft | Tokens can be revoked immediately. Rotate with grace period. |
| Brute force login | 5 failed attempts → 15 min account lock. Rate limit on `/auth/login` |
| SQL injection | SQLAlchemy parameterized queries — no raw SQL |
| Capability enumeration | Rate limit per agent. Audit log captures enumeration attempts |
| Cross-team access | TenantMiddleware enforces `team_namespace` on every DB query |
| Audit tampering | Append-only `audit_events` table. No UPDATE or DELETE on audit rows |
| OPA bypass | Fabric API enforces OPA evaluation — agents cannot skip it |
| Intra-pack confused-deputy | Identity-binding scope bounded by pack breadth. See below. |

### Intra-Pack Confused-Deputy Residual

**Threat:** A compromised or confused agent requests capability X on resource Y within its authorized pack, but the operator intended resource Z (different value, same pack). The request passes because both Y and Z are within the agent's identity-bound resource set.

**Mitigation:** Identity-bound resource policy (v0.2.0) blocks cross-identity redirects — an agent cannot request resources outside its assigned packs. This eliminates the confused-deputy attack surface across identities.

**Residual:** Intra-pack misuse survives. If an agent has access to 64 resources and a model-authored request targets resource #37 instead of resource #42, the request passes because both are in the pack.

**Effective catch rate (validated independent analysis):**

```
catch = 1 - (pack_size - 1) / (total_resources_in_domain - 1)
```

| Pack Size | Catch Rate (at R=512) |
|---|---|
| 1 resource | 100% (per-resource identity = full close) |
| 16 resources | ~97% |
| 64 resources | ~88% |
| R resources | 0% (one giant pack = no identity binding) |

**Recommendation:** This is a granularity problem, not a runtime enforcement problem. Narrower packs provide stronger protection. See [Pack Granularity Guide](docs/guides/pack-granularity.md) for guidance on sizing packs by capability sensitivity.

**Audit visibility:** Each audit event records the `pack_resource_count` and `total_resources_in_domain` at request time. Compliance teams can compute residual risk for historical requests.

## What to Expect

If a vulnerability is confirmed:

1. A fix will be developed and tested
2. A security advisory will be published with the fix
3. Credit will be given to the reporter (unless anonymity is requested)
