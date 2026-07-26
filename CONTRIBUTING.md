# Contributing to MCP Fabric

Thanks for your interest in contributing. MCP Fabric is a composable tool mesh for MCP ecosystems — server registry, capability normalization, trust policies, routing, and audit.

## Quick Start

```bash
git clone https://github.com/deghosal-2026/mcp-fabric.git
cd mcp-fabric
docker-compose up
```

The admin UI will be at `http://localhost:8000/admin`. You'll need at least one MCP server running locally to test the full flow. Any MCP-compliant server (filesystem, git, knowledge base) works.

## Project Structure

```
mcp-fabric/
├── api/               # FastAPI application
│   ├── registry/      # Server registration and inspection
│   ├── catalog/       # Capability normalization and mapping
│   ├── routing/       # Capability resolution and request routing
│   ├── policy/        # Trust levels, agent classes, policy evaluation
│   ├── audit/         # Request/denial/policy change logging
│   └── alerts/        # Proactive notifications
├── ui/                # React admin dashboard
├── migrations/        # Database migrations (Alembic)
├── tests/             # Test suite
├── docs/              # Documentation (PRD, architecture)
├── docker-compose.yml # Local dev stack
├── Dockerfile         # Production image
└── README.md
```

## Local Development

**Prerequisites:**
- Docker and Docker Compose
- Python 3.11+ (for running tests outside Docker)
- Node.js 18+ (for UI development)

**Run the stack:**

```bash
docker-compose up
```

This starts:
- Fabric API on `http://localhost:8000`
- Admin UI on `http://localhost:3000`
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`

**Run tests:**

```bash
pip install -r requirements-dev.txt
pytest tests/
```

**Run UI dev server:**

```bash
cd ui && npm install && npm run dev
```

## How to Contribute

1. **Find an issue** — check the [issues](https://github.com/deghosal-2026/mcp-fabric/issues) for `good-first-issue` or `help-wanted` tags.
2. **Fork and branch** — create a branch from `main` with a descriptive name (`feat/`, `fix/`, `docs/`).
3. **Make your change** — keep PRs focused on one thing.
4. **Add tests** — new features should include tests.
5. **Open a PR** — describe what you changed and why. Link the issue.

## Code Style

- Python: Black formatting, 88-char line length, type hints on public functions
- React: Prettier formatting, functional components, TypeScript
- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, `test:`)

## Testing Policy

- **Every new feature must include tests.** Major functionality added to the codebase must be accompanied by automated tests in the test suite.
- **Coverage targets:** Aim for ≥80% line coverage on new code. Pull requests that reduce overall coverage below the threshold will be flagged.
- **Test types:** Prefer unit tests for business logic, integration tests for API routes, and E2E tests for full-stack flows.
- **Running tests:** `pytest tests/ -v` — ensure all tests pass before opening a PR.
- **Test data:** Use fixtures and factories rather than production data. Never commit real credentials or tokens.

## Where to Start

Good first contributions:

- **Add a test MCP server fixture** — create a simple MCP server for the test suite
- **Improve capability mapping heuristics** — better auto-mapping from raw tool names to capability tags
- **Add a new admin UI view** — improve the dashboard with a metric or visualization you'd find useful
- **Write docs** — improve README, add tutorials, write about MCP governance patterns
- **Add a new MCP server integration** — test Fabric with a popular OSS MCP server and report/document the experience

## Questions?

Open a [discussion](https://github.com/deghosal-2026/mcp-fabric/discussions) or comment on the relevant issue. We're small and responsive.
