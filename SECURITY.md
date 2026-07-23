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

## What to Expect

If a vulnerability is confirmed:

1. A fix will be developed and tested
2. A security advisory will be published with the fix
3. Credit will be given to the reporter (unless anonymity is requested)
