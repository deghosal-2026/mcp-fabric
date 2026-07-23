import logging
import os

from passlib.hash import bcrypt
from sqlalchemy import func, select

from api.database import async_session
from api.models import AdminUser

logger = logging.getLogger(__name__)


async def bootstrap_admin_user():
    """Create the initial admin user if the admin table is empty."""
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(AdminUser))
        count = result.scalar()

        if count > 0:
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
