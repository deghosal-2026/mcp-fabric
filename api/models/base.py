"""Base SQLAlchemy declarative model, plus reusable mixins for every table.

UUIDMixin  – Primary-key column of type UUID with auto-generation (uuid4).
              Every entity table in the fabric uses UUIDs as its PK so that
              IDs are unpredictable and safe to expose in API responses.
TimestampMixin – A single `created_at` column with server-side default now().
              Tables that need this should also inherit TimestampMixin.
Base       – The single DeclarativeBase all ORM models inherit from.
              Alembic tracks Base.metadata to detect schema migrations.
"""

import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Root declarative base. Every ORM model in the fabric inherits from this.

    Attributes:
        metadata: Central registry of all mapped tables. Alembic reads this to
                  generate migration revisions automatically.
    """

    pass


class TimestampMixin:
    """Mixin that adds a `created_at` timestamp column.

    Usage:
        class MyModel(UUIDMixin, TimestampMixin, Base):
            ...

    The server_default=func.now() means the DB sets the timestamp at INSERT
    time, so the value is consistent even across replicas.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UUIDMixin:
    """Mixin that adds a UUID primary-key column named `id`.

    - uuid4 is used (random UUID, not timestamp-based) for security.
    - primary_key=True makes this the clustered index on every table.
    - No autoincrement integer PK is used anywhere in the fabric; UUIDs avoid
      enumeration attacks and simplify distributed ID generation.
    """

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
