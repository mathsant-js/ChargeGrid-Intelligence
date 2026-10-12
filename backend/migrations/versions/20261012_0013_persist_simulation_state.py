"""Persist simulator clock checkpoint.

Revision ID: 20261012_0013
Revises: 20260924_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261012_0013"
down_revision: str | None = "20260924_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "simulation_state",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("singleton_key", sa.Boolean(), nullable=False),
        sa.Column("current_instant", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_tick", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("singleton_key"),
    )


def downgrade() -> None:
    op.drop_table("simulation_state")
