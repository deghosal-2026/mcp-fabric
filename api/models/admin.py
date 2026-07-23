"""ORM models for admin users and background task tracking.

AdminUser stores credentials, roles, and MFA state.
BackgroundTask correlates Celery jobs back to the API.
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Index, Integer, String, Text, func

from api.models.base import Base, UUIDMixin


class AdminUser(UUIDMixin, Base):
    """A human operator with elevated privileges in the fabric."""

    __tablename__ = "admin_users"

    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(512), nullable=False)
    role = Column(String(50), nullable=False)
    team_namespace = Column(String(100), nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(512), nullable=True)
    status = Column(String(50), default="active")
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    password_history = Column(JSON, nullable=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)


class BackgroundTask(UUIDMixin, Base):
    """Tracks the lifecycle of an async Celery task."""

    __tablename__ = "background_tasks"

    celery_task_id = Column(String(255), nullable=True)
    task_type = Column(String(100), nullable=False)
    status = Column(String(50), default="pending")
    params = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_bgtasks_status", "status"),
        Index("idx_bgtasks_celery", "celery_task_id"),
    )
