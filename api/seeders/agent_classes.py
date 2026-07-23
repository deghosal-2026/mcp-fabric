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
    """Seed default agent classes if they do not already exist."""
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
