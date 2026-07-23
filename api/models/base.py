"""Declarative base and reusable ORM mixins.

All models inherit from Base (DeclarativeBase) and optionally from
TimestampMixin (created_at) and UUIDMixin (UUID primary key).
"""

import uuid

from sqlalchemy import UUID, Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""


class TimestampMixin:
    """Adds a server-default created_at timestamp column."""

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UUIDMixin:
    """Adds a UUID primary key column with auto-generated values."""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
