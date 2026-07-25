"""Default agent class seeder.

Creates the initial set of AgentClass records that define role-based
access levels for agents. Each class represents a persona with different
capabilities — from full admin access to restricted new-hire access.

Idempotency:
    - Each class is looked up by name before insertion.
    - Existing classes are never modified or duplicated.
    - The seeder can be safely run on every startup.

Default classes and their intended use:
    - agent:admin — Full access to all tools and capabilities.
    - agent:incident-responder — Read monitoring, write incident tools.
    - agent:deploy-monitor — Deployment and infrastructure monitoring.
    - agent:code-reviewer — Code review and quality analysis tools.
    - agent:developer — General development tools, sandboxed execution.
    - agent:new-hire — Restricted, read-only, requires approval for
      destructive operations.
"""

from sqlalchemy import select

from api.database import async_session
from api.models import AgentClass

DEFAULT_AGENT_CLASSES = [
    {"name": "agent:admin", "description": "Full access to all tools and capabilities"},
    {
        "name": "agent:incident-responder",
        "description": "Read access to monitoring, write to incident tools",
    },
    {
        "name": "agent:deploy-monitor",
        "description": "Deployment and infrastructure monitoring tools",
    },
    {"name": "agent:code-reviewer", "description": "Code review and quality analysis tools"},
    {
        "name": "agent:developer",
        "description": "General development tools and sandboxed execution",
    },
    {
        "name": "agent:new-hire",
        "description": (
            "Restricted access, read-only tools, requires approval for destructive operations"
        ),
    },
]


async def seed_agent_classes():
    """Seed default agent classes if they do not already exist.

    Iterates over DEFAULT_AGENT_CLASSES and creates each one that does
    not already exist in the database (matched by name). Runs in a single
    transaction — all inserts succeed or none do.

    Idempotent: safe to call multiple times. Only missing records are
    created; existing records are left untouched.
    """
    async with async_session() as session:
        for cls_data in DEFAULT_AGENT_CLASSES:
            result = await session.execute(
                select(AgentClass).where(AgentClass.name == cls_data["name"])
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                continue
            session.add(AgentClass(**cls_data))
        await session.commit()
