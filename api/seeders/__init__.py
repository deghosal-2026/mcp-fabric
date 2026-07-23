"""Orchestrates database seeding on application startup.

Agent classes and alert rules seed in parallel; admin bootstrap
runs after both finish.
"""

import asyncio

from api.seeders.admin_bootstrap import bootstrap_admin_user
from api.seeders.agent_classes import seed_agent_classes
from api.seeders.alert_rules import seed_alert_rules


async def run_seeders():
    await asyncio.gather(seed_agent_classes(), seed_alert_rules())
    await bootstrap_admin_user()
