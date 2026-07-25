# Changelog

All notable changes to MCP Fabric will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Advanced routing engine (health/latency/fallback-aware)
- Multi-tenant scopes and namespace isolation
- Performance benchmarks and caching improvements

## [v0.1.0] — 2026-07-25

### Added
- MCP server registry with auto-discovery of tools
- Normalized capability catalog with deprecation lifecycle
- OPA Rego policy engine for access decisions
- Agent classes with identity token management
- Capability packs — bundle and assign to agent classes
- Human-in-the-loop approvals for gated capabilities
- Audit log with event filtering and JSON export
- Trust posture dashboard with per-class trust levels
- Operational alerts for server health and security issues
- Admin user management with RBAC (Admin/Editor/Viewer) and MFA
- Dashboard with stat cards and recent activity panels
- 474 automated tests (backend, UI, OPA, E2E)

### Fixed
- 170 mypy type errors across 41 files (strict mode)
- 32 ruff lint errors (unused imports, line length, import sorting)
- Webhook routes now enforce agent_id ownership
- Admin self-deactivation guard
- MFA verify/recover moved into service layer
- Capability mapping creation moved into service layer
- CI pipeline with 6 parallel jobs (lint, typecheck, tests, OPA, UI)

### Security
- Auth middleware skips health/metrics endpoints
- Webhook routes enforce agent_id match via request.state.agent_id
- Self-deactivation prohibited for admin accounts

[Unreleased]: https://github.com/deghosal-2026/mcp-fabric/compare/v0.1.0...HEAD
[v0.1.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.1.0
