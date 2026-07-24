# MCP Fabric — opencode Agents

## Code Review Agent

Reviews use the `general` subagent with Deepseek V4 Pro for thorough analysis.

### Review Scope
- **Correctness**: Logic matches spec, edge cases handled
- **Style**: Ruff lint rules (E, F, I, N, W, UP, B, C4, SIM), line-length 100
- **Types**: mypy strict mode
- **Coverage**: Unit tests for new services/utilities
- **Error handling**: All error paths return structured `FabricError` responses

### Workflow
1. Run `make lint` before requesting review
2. Run `make typecheck` before requesting review
3. Run `poetry run pytest tests/ -v` before requesting review
4. Open review with `/review` command

### Review Checklist
- [ ] Imports sorted (I)
- [ ] No bare `except:` — specific exception types only
- [ ] Async functions use `async/await`, not `asyncio.run()`
- [ ] Pydantic schemas use `model_config` for ORM mapping
- [ ] Alembic migrations run forward and backward cleanly
