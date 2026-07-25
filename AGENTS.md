# MCP Fabric — opencode Agents

This file guides AI agents (opencode, Claude Code, etc.) when working with the MCP Fabric
codebase. Follow these conventions, workflows, and checklist items during every session.

---

## Code Review Agent

Reviews use the `general` subagent with Deepseek V4 Pro for thorough analysis.

### Review Scope

- **Correctness**: Logic matches spec, edge cases handled.
  - Verify that SQLAlchemy queries use the correct joins, filters, and async patterns.
  - Ensure Pydantic schemas validate input/output correctly (types, optional fields, defaults).
  - Check that router endpoints return proper HTTP status codes (200, 201, 204, 400, 403, 404, 409, 422, 500).

- **Style**: Ruff lint rules (E, F, I, N, W, UP, B, C4, SIM), line-length 100.
  - All PRs and commits must pass `ruff check` and `ruff format --check` before merging.
  - Imports follow the `I` rule: stdlib → third-party → local, alphabetically sorted per block.

- **Types**: mypy strict mode.
  - Every function signature must have type annotations for parameters and return values.
  - Use `| None` for optional types (Python 3.12+), not `Optional[]`.
  - Avoid `Any` unless absolutely necessary; prefer `object`, `TypeVar`, or `Protocol`.

- **Coverage**: Unit tests for new services/utilities.
  - New services (under `api/services/`) need a corresponding test file under `tests/services/`.
  - Aim for ≥80% line coverage on new code; use `pytest-cov` to measure.
  - Integration tests under `tests/` that hit real routes with a test DB are preferred over pure unit mocks.

- **Error handling**: All error paths return structured `FabricError` responses.
  - `FabricError` is defined in `api/schemas/common.py` and includes `detail`, `code`, and optional `field` keys.
  - Never raise bare `HTTPException`; always use the helpers in `api/errors.py`.
  - Catch specific exception types (e.g., `IntegrityError`, `ValidationError`), never bare `except:`.

### Workflow

1. Run `make lint` before requesting review.
   - Equivalent to `ruff check api/ tests/ && ruff format --check api/ tests/`.
   - Fix all errors before proceeding; use `ruff check --fix` for auto-fixable issues.

2. Run `make typecheck` before requesting review.
   - Equivalent to `poetry run mypy api/`.
   - Address all `error:` lines; warnings (prefixed with `note:`) are advisory but should be cleaned up.

3. Run `poetry run pytest tests/ -v` before requesting review.
   - Ensure all tests pass, not just the ones related to your change.
   - Use `-x` to stop on first failure for faster iteration, but remove before final check.

4. Open review with `/review` command.
   - The review agent will inspect the full diff, run mental checks against the checklist,
     and return a structured report with confidence scores.

### Review Checklist

- [ ] Imports sorted (I) — run `ruff check --fix` to auto-sort.
- [ ] No bare `except:` — specific exception types only (e.g., `except ValueError:`).
- [ ] Async functions use `async/await`, not `asyncio.run()` — `asyncio.run()` blocks the event loop.
- [ ] Pydantic schemas use `model_config` for ORM mapping — e.g., `model_config = {"from_attributes": True}`.
- [ ] Alembic migrations run forward and backward cleanly — test with `alembic upgrade head` then `alembic downgrade -1`.

---

## CI Troubleshooting

Refer to this section when CI fails in GitHub Actions.

### Common Failure Patterns

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| `poetry lock --no-update` fails | Poetry v2 removed `--no-update` | Remove the flag; use `poetry lock && poetry install` |
| `No file/folder found for package` | Missing `[tool.poetry.packages]` in `pyproject.toml` | Add `packages = [{ include = "api", from = "." }]` |
| `npm ci` ERESOLVE on TypeScript | npm 11+ stricter peer dep checking | Add `--legacy-peer-deps` to `npm ci` commands |
| Ruff lint fails with E501 | Line exceeds 100-char limit | Split code into multi-line, or use `# noqa: E501` on data literals |
| TypeScript 7.x vs typescript-eslint | `typescript-eslint` peer requires `<6.1.0` | Pin typescript to `~6.0.2` or upgrade typescript-eslint |

### CI Workflow Structure

The CI workflow (`.github/workflows/ci.yml`) runs these jobs in parallel:

| Job | Command | Depends On |
|-----|---------|-----------|
| `lint` | `ruff check && ruff format --check` | Nothing |
| `typecheck` | `poetry run mypy api/` | Python deps installed |
| `test-sqlite` | `pytest -m "unit"` with SQLite + Redis | Python deps + Redis service container |
| `opa-tests` | `opa test policies/` | OPA binary |
| `ui-lint` | `npm run lint && npm run typecheck` | Node deps installed |
| `ui-test` | `npx vitest run` | Node deps installed |

---

## Dependency Management

### Python Dependencies

- Declared in `pyproject.toml` under `[project.dependencies]` and `[project.optional-dependencies.dev]`.
- Locked in `poetry.lock` — commit this file.
- To add: `poetry add <package>` (runtime) or `poetry add --group dev <package>` (dev).
- To update: edit `pyproject.toml` version constraints, then run `poetry lock && poetry install`.
- CI runs `poetry lock && poetry install` to regenerate the lock file from scratch (Poetry v2 behavior).

### UI / Node Dependencies

- Declared in `ui/package.json`.
- Locked in `ui/package-lock.json` — commit this file.
- To add: `cd ui && npm install <package>`.
- To update: `cd ui && npm update <package>`.
- CI runs `npm ci --legacy-peer-deps` to install from the lock file with relaxed peer-dep checking.

---

## Project Structure

```
api/                # Python backend (FastAPI)
├── cli.py          # CLI entrypoint (fabric-admin)
├── dependencies.py # FastAPI dependency injection
├── errors.py       # Structured error helpers
├── models/         # SQLAlchemy ORM models
├── routers/        # FastAPI route handlers
├── schemas/        # Pydantic request/response schemas
├── seeders/        # Database demo data seeders
├── services/       # Business logic layer
alembic/            # Database migrations
tests/              # Test suite (pytest)
ui/                 # Frontend (React + Vite)
├── src/            # React components, pages, hooks
├── e2e/            # Playwright end-to-end tests
policies/           # OPA (Open Policy Agent) policies
monitoring/         # Alert rules, dashboards
```
