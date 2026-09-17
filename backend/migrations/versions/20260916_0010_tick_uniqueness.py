"""Prevent duplicate readings for one simulated instant.

Revision ID: 20260916_0010
Revises: 20260916_0009
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260916_0010"
down_revision: str | None = "20260916_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("energy_readings") as batch_op:
        batch_op.create_unique_constraint(
            "uq_energy_readings_session_tick", ["session_id", "timestamp"]
        )
    with op.batch_alter_table("solar_readings") as batch_op:
        batch_op.create_unique_constraint(
            "uq_solar_readings_station_tick", ["station_id", "timestamp"]
        )


def downgrade() -> None:
    with op.batch_alter_table("solar_readings") as batch_op:
        batch_op.drop_constraint("uq_solar_readings_station_tick", type_="unique")
    with op.batch_alter_table("energy_readings") as batch_op:
        batch_op.drop_constraint("uq_energy_readings_session_tick", type_="unique")
