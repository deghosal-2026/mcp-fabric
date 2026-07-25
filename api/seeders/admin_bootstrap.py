"""Bootstraps the first admin user from environment variables.

Creates an initial admin user when the admin table is empty so that
operators can log in immediately after deployment without manual
database setup.

This is a one-shot bootstrap: after the first admin user exists
(either created by this seeder or manually), subsequent runs are
no-ops. The seeder checks count > 0 and returns early.

Environment variables:
    - FABRIC_ADMIN_EMAIL (required): Email address for the admin user.
    - FABRIC_ADMIN_PASSWORD (required): Password (hashed with bcrypt
      before storage).

If either env var is missing when the admin table is empty, a warning
is logged but no error is raised — the application can still start
and an admin can be created through the API later.

Idempotency:
    - Checks if AdminUser table has any records before attempting insert.
    - Does NOT update existing admin users.
    - Does NOT guarantee only one admin exists — if multiple seeders
      run concurrently, multiple could be created (unlikely in practice).
"""

import logging
import os

from passlib.hash import bcrypt
from sqlalchemy import func, select

from api.database import async_session
from api.models import AdminUser

logger = logging.getLogger(__name__)


async def bootstrap_admin_user() -> None:
    """Create the initial admin user if the admin table is empty.

    Reads FABRIC_ADMIN_EMAIL and FABRIC_ADMIN_PASSWORD from environment
    variables, hashes the password with bcrypt, and creates an AdminUser
    record with role="admin" and status="active".

    Skips silently if any admin users already exist. Logs a warning if
    the table is empty but the required env vars are not set.

    Idempotent: safe to call multiple times (checks count before insert).
    """
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(AdminUser))
        count = result.scalar()

        if count is not None and count > 0:
            return

        email = os.getenv("FABRIC_ADMIN_EMAIL")
        password = os.getenv("FABRIC_ADMIN_PASSWORD")

        if email and password:
            user = AdminUser(
                username="admin",
                email=email,
                password_hash=bcrypt.hash(password),
                role="admin",
                status="active",
            )
            session.add(user)
            await session.commit()
            logger.info("Bootstrapped admin user: %s", email)
        else:
            logger.warning(
                "No admin users exist and FABRIC_ADMIN_EMAIL/PASSWORD not set. "
                "Set both env vars to bootstrap an admin user."
            )
