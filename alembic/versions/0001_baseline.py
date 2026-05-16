"""Baseline migration: delegates to db.py::init_schema().

After this, future migrations are written by hand against the live schema
(no autogenerate — we don't use SQLAlchemy ORM models).

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-16 00:00:00.000000
"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Run the canonical schema from backend/db.py.
    from db import init_schema  # type: ignore
    init_schema()


def downgrade() -> None:
    # Refuse to drop the schema accidentally — destructive baseline downgrade is unsafe.
    raise NotImplementedError("Baseline downgrade is intentionally not supported.")
