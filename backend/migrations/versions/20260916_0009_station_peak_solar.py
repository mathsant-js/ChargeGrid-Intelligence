"""Add station peak solar power.

Revision ID: 20260916_0009
Revises: 20260901_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260916_0009"
down_revision: str | None = "20260901_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("charging_stations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "station_peak_solar_kw",
                sa.Float(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.create_check_constraint(
            "ck_stations_peak_solar_nonnegative", "station_peak_solar_kw >= 0"
        )


def downgrade() -> None:
    with op.batch_alter_table("charging_stations") as batch_op:
        batch_op.drop_constraint("ck_stations_peak_solar_nonnegative", type_="check")
        batch_op.drop_column("station_peak_solar_kw")
