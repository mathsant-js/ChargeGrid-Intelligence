"""Add the configurable high-solar alert threshold.

Revision ID: 20260924_0012
Revises: 20260916_0011
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_0012"
down_revision: str | None = "20260916_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "system_configurations",
        sa.Column(
            "high_solar_availability_threshold",
            sa.Float(),
            server_default="0.8",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_config_high_solar_availability_range",
        "system_configurations",
        "high_solar_availability_threshold > 0 "
        "AND high_solar_availability_threshold <= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_config_high_solar_availability_range",
        "system_configurations",
        type_="check",
    )
    op.drop_column("system_configurations", "high_solar_availability_threshold")
