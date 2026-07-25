"""Orchestrates database seeding on application startup.

Agent classes and alert rules seed in parallel (they have no dependency
on each other); admin bootstrap runs after both finish because the admin
user may reference default agent classes.

Idempotency:
    - All seeders check for existing records before inserting (name-based
      lookup for agent classes and alert rules, count-based for admin).
    - Running the seeders multiple times is safe — only missing records
      are created.
    - No records are deleted or modified, only added.

Execution order:
    1. seed_agent_classes() — creates default AgentClass records.
    2. seed_alert_rules() — creates default AlertRule records.
    (Steps 1 and 2 run concurrently via asyncio.gather.)
    3. bootstrap_admin_user() — creates the first AdminUser if the
       admins table is empty and environment variables are set.
"""

import asyncio
import os

from api.database import async_session
from api.seeders.admin_bootstrap import bootstrap_admin_user
from api.seeders.agent_classes import seed_agent_classes
from api.seeders.alert_rules import seed_alert_rules
from api.seeders.demo_data import seed_demo_data


async def run_seeders():
    """Run all database seeders in dependency order.

    Agent classes and alert rules are independent and seed concurrently.
    Admin bootstrap runs after both because it is a separate concern
    (user management vs. system configuration) and should not block
    the system-level seeders.
    """
    await asyncio.gather(seed_agent_classes(), seed_alert_rules())
    await bootstrap_admin_user()
    if os.getenv("FABRIC_SEED_DEMO_DATA") == "1":
        async with async_session() as session:
            await seed_demo_data(session)
