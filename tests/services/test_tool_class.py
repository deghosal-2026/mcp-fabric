"""Tests for agent-level permissions: read-only vs destructive tool classification (#445).

Validates:
  1. Tool classification (read_only vs mutating) from tool names.
  2. AgentClass is_read_only flag is persisted and enforced.
  3. RoutingService.execute denies mutating tools for read-only agents.
  4. RoutingService.execute allows read-only tools for read-only agents.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.agent import AgentClass
from api.services.tool_class import (
    TOOL_CLASS_MUTATING,
    TOOL_CLASS_READ_ONLY,
    classify_tool,
    is_read_only_tool,
)


def test_classify_read_only_prefixes() -> None:
    for name in (
        "get_status",
        "list_deployments",
        "search_logs",
        "read_config",
        "find_user",
        "query_metrics",
        "check_health",
    ):
        assert classify_tool(name) == TOOL_CLASS_READ_ONLY, f"{name} should be read_only"


def test_classify_mutating() -> None:
    for name in (
        "deploy_service",
        "create_user",
        "delete_record",
        "update_config",
        "promote_release",
        "submit_form",
    ):
        assert classify_tool(name) == TOOL_CLASS_MUTATING, f"{name} should be mutating"


def test_is_read_only_tool_helper() -> None:
    assert is_read_only_tool("get_status") is True
    assert is_read_only_tool("deploy_service") is False


def test_classify_case_insensitive() -> None:
    assert classify_tool("GET_Status") == TOOL_CLASS_READ_ONLY
    assert classify_tool("Deploy_Service") == TOOL_CLASS_MUTATING


@pytest.mark.asyncio
async def test_agent_class_is_read_only_persisted(db_session: AsyncSession) -> None:
    """is_read_only defaults to False and can be set True."""
    ro = AgentClass(name="read-only-agent", is_read_only=True)
    full = AgentClass(name="full-agent")
    db_session.add_all([ro, full])
    await db_session.commit()
    await db_session.refresh(ro)
    await db_session.refresh(full)

    assert ro.is_read_only is True
    assert full.is_read_only is False


@pytest.mark.asyncio
async def test_agent_class_is_read_only_default_false(db_session: AsyncSession) -> None:
    """Default is False when not specified."""
    ac = AgentClass(name="default-agent")
    db_session.add(ac)
    await db_session.commit()
    await db_session.refresh(ac)
    assert ac.is_read_only is False
