"""Create the Phase 1 database baseline.

Revision ID: 20260818_0001
Revises:
Create Date: 2026-08-18
"""

revision = "20260818_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Establish an Alembic baseline before domain tables are introduced."""


def downgrade() -> None:
    """The baseline does not create database objects."""
