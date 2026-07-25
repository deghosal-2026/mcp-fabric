"""Seed a realistic demo dataset for local UI exploration.

This seeder is intentionally idempotent. It creates a stable set of demo
records the first time it runs and skips subsequent runs if the marker server
already exists.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.admin import AdminUser
from api.models.agent import (
    AgentClass,
    AgentClassPack,
    AgentIdentity,
    CapabilityPack,
    PackAssignment,
    TrustAssignment,
)
from api.models.audit import AlertEvent, AlertRule, ApprovalRequest, AuditEvent
from api.models.capability import Capability
from api.models.server import CapabilityMapping, MCPServer, ServerTool
from api.services.auth_service import AuthService

DEMO_PREFIX = "demo:"
DEMO_NAMESPACE = "team:demo"
DEMO_MARKER_SERVER = f"{DEMO_PREFIX}server-01"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_demo_data(db: AsyncSession) -> None:
    existing = await db.execute(select(MCPServer).where(MCPServer.name == DEMO_MARKER_SERVER))
    if existing.scalar_one_or_none() is not None:
        return

    now = _now()
    auth = AuthService(db=db)

    existing_admin_rows = (await db.execute(select(AdminUser))).scalars().all()
    existing_admins_by_email = {admin.email: admin for admin in existing_admin_rows}
    existing_admins_by_username = {admin.username: admin for admin in existing_admin_rows}
    admin_specs = [
        ("admin", "admin@mcp-fabric.local", "admin", DEMO_NAMESPACE, False),
        ("priya", "priya@example.com", "admin", "team:platform", True),
        ("alex", "alex@example.com", "editor", "team:platform", False),
        ("jordan", "jordan@example.com", "viewer", "team:security", True),
    ]
    admins: list[AdminUser] = []
    for username, email, role, team_namespace, mfa_enabled in admin_specs:
        admin = existing_admins_by_email.get(email) or existing_admins_by_username.get(username)
        if admin is None:
            admin = AdminUser(
                username=username,
                email=email,
                password_hash=auth.hash_password("Admin123!"),
                role=role,
                team_namespace=team_namespace,
                mfa_enabled=mfa_enabled,
                status="active",
            )
            db.add(admin)
        admins.append(admin)

    agent_classes = [
        AgentClass(name=f"{DEMO_PREFIX}agent-admin", description="Demo admin agent", team_namespace=DEMO_NAMESPACE),
        AgentClass(name=f"{DEMO_PREFIX}incident-responder", description="Incident automation", team_namespace="team:platform"),
        AgentClass(name=f"{DEMO_PREFIX}developer", description="Developer assistant", team_namespace="team:platform"),
        AgentClass(name=f"{DEMO_PREFIX}new-hire", description="New hire sandbox", team_namespace="team:platform"),
        AgentClass(name=f"{DEMO_PREFIX}security", description="Security review agent", team_namespace="team:security"),
        AgentClass(name=f"{DEMO_PREFIX}deploy-monitor", description="Deployment monitor", team_namespace="team:platform"),
    ]
    db.add_all(agent_classes)

    capabilities = [
        Capability(name=f"{DEMO_PREFIX}knowledge:search", domain="knowledge", description="Search knowledge base", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}knowledge:runbook-get", domain="knowledge", description="Get runbook", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}code:search", domain="code", description="Search code", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}code:blameless-diff", domain="code", description="Review recent changes", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}deployment:status", domain="deployment", description="Check deployment status", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}deployment:promote", domain="deployment", description="Promote deployment", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}service:health-metrics", domain="service", description="Read health metrics", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}incident:create", domain="incident", description="Create incident", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}incident:get", domain="incident", description="Get incident details", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}vulnerability:scan", domain="security", description="Run vulnerability scan", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}dependency:impact-analysis", domain="dependency", description="Assess dependency impact", status="active", grace_period_days=14, created_by="demo-seeder"),
        Capability(name=f"{DEMO_PREFIX}cost:estimate", domain="cost", description="Estimate cloud cost", status="active", grace_period_days=14, created_by="demo-seeder"),
    ]
    db.add_all(capabilities)

    packs = [
        CapabilityPack(name=f"{DEMO_PREFIX}new-hire-pack", description="Starter tools", team_namespace="team:platform"),
        CapabilityPack(name=f"{DEMO_PREFIX}incident-pack", description="Incident response tools", team_namespace="team:platform"),
        CapabilityPack(name=f"{DEMO_PREFIX}security-pack", description="Security analysis tools", team_namespace="team:security"),
    ]
    db.add_all(packs)

    await db.flush()

    server_specs = [
        (DEMO_MARKER_SERVER, "Demo Knowledge", "platform", "trusted", "healthy"),
        (f"{DEMO_PREFIX}server-02", "Docs Search", "platform", "trusted", "healthy"),
        (f"{DEMO_PREFIX}server-03", "Code Search", "platform", "trusted", "healthy"),
        (f"{DEMO_PREFIX}server-04", "Git History", "platform", "trusted", "degraded"),
        (f"{DEMO_PREFIX}server-05", "Deploy Control", "platform", "approval-gated", "healthy"),
        (f"{DEMO_PREFIX}server-06", "Metrics", "platform", "trusted", "healthy"),
        (f"{DEMO_PREFIX}server-07", "Incident Ops", "platform", "trusted", "healthy"),
        (f"{DEMO_PREFIX}server-08", "Vuln Scanner", "security", "restricted", "degraded"),
        (f"{DEMO_PREFIX}server-09", "Dependency Graph", "platform", "trusted", "healthy"),
        (f"{DEMO_PREFIX}server-10", "Cost Explorer", "finance", "unreviewed", "unhealthy"),
        (f"{DEMO_PREFIX}server-11", "Canary Deploy", "platform", "approval-gated", "healthy"),
        (f"{DEMO_PREFIX}server-12", "Sandbox Tools", "data", "restricted", "healthy"),
    ]

    servers: list[MCPServer] = []
    for index, (name, description, owner_team, trust_level, health_status) in enumerate(server_specs, start=1):
        server = MCPServer(
            name=name,
            endpoint=f"https://{name.replace(':', '-').replace('_', '-')}.example.internal/mcp",
            owner_team=owner_team,
            description=description,
            labels=["demo", owner_team, health_status],
            trust_level=trust_level,
            health_status=health_status,
            team_namespace=f"team:{owner_team}",
            version="1.0.0",
            last_health_check=now - timedelta(minutes=index),
            updated_at=now - timedelta(minutes=index),
        )
        servers.append(server)
        db.add(server)

    await db.flush()

    tool_names = [
        "search_docs",
        "get_runbook",
        "search_code",
        "recent_diff",
        "deployment_status",
        "promote_deployment",
        "health_metrics",
        "create_incident",
        "get_incident",
        "scan_vulnerabilities",
        "impact_analysis",
        "estimate_cost",
    ]
    tools: list[ServerTool] = []
    for server, tool_name in zip(servers, tool_names, strict=False):
        tool = ServerTool(
            server_id=server.id,
            tool_name=tool_name,
            description=f"Demo tool {tool_name}",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            output_schema={"type": "object"},
        )
        tools.append(tool)
        db.add(tool)

    await db.flush()

    for capability, server, tool in zip(capabilities, servers, tools, strict=False):
        db.add(
            CapabilityMapping(
                capability_id=capability.id,
                server_id=server.id,
                tool_name=tool.tool_name,
                input_mapping={"query": "query"},
                output_mapping={"result": "result"},
                is_primary=True,
                routing_weight=1.0,
            )
        )

    for capability in capabilities[:4]:
        db.add(PackAssignment(pack_id=packs[0].id, capability_id=capability.id))
    for capability in capabilities[3:8]:
        db.add(PackAssignment(pack_id=packs[1].id, capability_id=capability.id))
    for capability in capabilities[8:12]:
        db.add(PackAssignment(pack_id=packs[2].id, capability_id=capability.id))

    db.add_all(
        [
            AgentClassPack(agent_class_id=agent_classes[0].id, pack_id=packs[0].id),
            AgentClassPack(agent_class_id=agent_classes[1].id, pack_id=packs[1].id),
            AgentClassPack(agent_class_id=agent_classes[4].id, pack_id=packs[2].id),
        ]
    )

    identities: list[AgentIdentity] = []
    for index, agent_class in enumerate(agent_classes[:4], start=1):
        identity = AgentIdentity(
            name=f"{DEMO_PREFIX}identity-{index:02d}",
            agent_class_id=agent_class.id,
            token_hash=auth.hash_password(f"demo-token-{index}"),
            token_prefix=f"demo-{index}",
            status="active",
            rate_limit_per_min=100,
        )
        identities.append(identity)
        db.add(identity)

    for agent_class in agent_classes[:4]:
        for server in servers[:2]:
            db.add(
                TrustAssignment(
                    agent_class_id=agent_class.id,
                    server_id=server.id,
                    trust_level="trusted",
                    tool_scope=None,
                )
            )
    db.add(
        TrustAssignment(
            agent_class_id=agent_classes[1].id,
            server_id=servers[4].id,
            trust_level="approval-gated",
            tool_scope=None,
        )
    )
    db.add(
        TrustAssignment(
            agent_class_id=agent_classes[4].id,
            server_id=servers[7].id,
            trust_level="restricted",
            tool_scope={"tools": ["scan_vulnerabilities"]},
        )
    )

    await db.flush()

    approval_statuses = ["pending", "approved", "denied", "pending", "approved", "denied", "pending", "approved"]
    for index, status in enumerate(approval_statuses):
        approval = ApprovalRequest(
            agent_identity_id=identities[index % len(identities)].id,
            capability_id=capabilities[index % len(capabilities)].id,
            server_id=servers[index % len(servers)].id,
            request_params={"service": f"service-{index}", "env": "staging" if index % 2 == 0 else "prod"},
            status=status,
            requested_at=now - timedelta(hours=index + 1),
            resolved_at=None if status == "pending" else now - timedelta(minutes=index * 5),
            approver_id=admins[0].id if status != "pending" else None,
            approver_note=None if status == "pending" else f"Demo {status}",
            expires_at=now + timedelta(hours=24 - index),
            result={"status": status} if status == "approved" else None,
        )
        db.add(approval)

    audit_events = [
        "server_registered",
        "policy_change",
        "approval_requested",
        "approval_approved",
        "approval_denied",
        "capability_request",
        "capability_mapped",
        "server_decommissioned",
        "alert_fired",
        "alert_acknowledged",
        "admin_invited",
        "trust_assignment_updated",
    ]
    for index, event_type in enumerate(audit_events):
        db.add(
            AuditEvent(
                event_type=event_type,
                actor_type="admin",
                actor_id=admins[index % len(admins)].username,
                target_type="server" if "server" in event_type else "capability",
                target_id=str(servers[index % len(servers)].id),
                details={"demo": True, "sequence": index},
                created_at=now - timedelta(minutes=index * 3),
            )
        )

    rules = [
        AlertRule(name=f"{DEMO_PREFIX}degraded-servers", alert_type="degraded_servers", condition={"threshold": 1}, channels=["log"], enabled=True),
        AlertRule(name=f"{DEMO_PREFIX}denied-requests", alert_type="denied_requests", condition={"threshold": 2}, channels=["log"], enabled=True),
    ]
    db.add_all(rules)
    await db.flush()

    for index in range(4):
        db.add(
            AlertEvent(
                rule_id=rules[index % len(rules)].id,
                message=f"Demo alert {index + 1}",
                details={"server": servers[index].name},
                fired_at=now - timedelta(minutes=index * 7),
                acknowledged_at=None if index % 2 == 0 else now - timedelta(minutes=index * 5),
                acknowledged_by=None if index % 2 == 0 else admins[0].id,
            )
        )

    await db.commit()
