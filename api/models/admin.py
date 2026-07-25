"""AdminUser and BackgroundTask ORM models for the fabric admin panel.

AdminUser   – Represents a human administrator who can log into the fabric
              dashboard, manage servers/capabilities/policies, and approve or
              deny agent capability requests (approval-gated flow).
BackgroundTask – Tracks long-running async jobs (e.g. bundle deployments,
              bulk imports) so the admin UI can poll for status.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, UUIDMixin


class AdminUser(UUIDMixin, Base):
    """Fabric admin user with authentication, MFA, and role-based access.

    Table: admin_users

    Relationships:
        - Referenced by ApprovalRequest.approver_id (FK -> admin_users.id)
        - Referenced by AlertEvent.acknowledged_by (FK -> admin_users.id)

    Columns:
        username (unique)      – Login username, also used in audit logs as actor label.
        email (unique)         – Contact / password-reset destination.
        password_hash          – Argon2id or bcrypt hash (never plaintext).
        role                   – 'admin', 'editor', or 'viewer' (enforced at schema layer).
        team_namespace         – Optional team scope for multi-tenant setups. An admin
                                 with a team_namespace can only manage resources in that
                                 namespace.
        mfa_enabled            – Whether TOTP MFA is active for this account.
        mfa_secret             – Encrypted TOTP seed (never returned in API responses).
        status                 – 'active', 'inactive', or 'suspended'.
        last_login_at          – Tracks last successful authentication for auditing.
        created_at             – Account creation timestamp.
        password_history (JSON)– List of previous password hashes to prevent reuse.
        recovery_codes (JSON)  – One-time-use recovery codes for MFA bypass.
        failed_attempts        – Consecutive failed login counter (for lockout).
        locked_until           – If set, login is blocked until this timestamp.
    """

    __tablename__ = "admin_users"

    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    team_namespace: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mfa_enabled: Mapped[bool | None] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    password_history: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    recovery_codes: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    failed_attempts: Mapped[int | None] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BackgroundTask(UUIDMixin, Base):
    """Async job tracker for long-running fabric operations.

    Table: background_tasks

    When the admin invokes a slow operation (e.g. deploying a large OPA bundle),
    the API creates a BackgroundTask row, kicks off a Celery task, and returns
    the task ID immediately. The admin UI polls GET /tasks/{id} to check status.

    Indexes:
        idx_bgtasks_status  – Fast filtering by status (pending/running/done/failed).
        idx_bgtasks_celery  – Lookup by Celery task_id for reconciling task state.

    Columns:
        celery_task_id – ID assigned by Celery for the background worker.
        task_type      – Discriminator: 'bundle_deploy', 'bulk_import', etc.
        status         – 'pending' -> 'running' -> 'done' | 'failed'.
        params (JSON)  – Input parameters that were passed to the task.
        result (JSON)  – Output produced by the task on success.
        error          – Stack trace or error message if the task failed.
        created_at     – When the task was queued.
        completed_at   – When the task finished (success or failure).
    """

    __tablename__ = "background_tasks"

    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), default="pending")
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_bgtasks_status", "status"),
        Index("idx_bgtasks_celery", "celery_task_id"),
    )
