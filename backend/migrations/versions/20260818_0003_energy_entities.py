"""Create charging sessions and energy and solar readings.

Revision ID: 20260818_0003
Revises: 20260818_0002
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0003"
down_revision: str | None = "20260818_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

session_status = sa.Enum(
    "CREATED",
    "CHARGING",
    "PAUSED",
    "COMPLETED",
    "CANCELLED",
    name="charging_session_status",
    native_enum=False,
)


def timestamp_column(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "charging_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("charger_id", sa.Uuid(), nullable=False),
        sa.Column("status", session_status, server_default="CREATED", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_power_kw", sa.Float(), nullable=False),
        sa.Column("allocated_power_kw", sa.Float(), server_default="0", nullable=False),
        sa.Column("energy_consumed_kwh", sa.Float(), server_default="0", nullable=False),
        sa.Column("solar_energy_kwh", sa.Float(), server_default="0", nullable=False),
        sa.Column("grid_energy_kwh", sa.Float(), server_default="0", nullable=False),
        sa.Column("tariff_per_kwh", sa.Numeric(12, 4), nullable=False),
        sa.Column("total_cost", sa.Numeric(14, 2), server_default="0", nullable=False),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "requested_power_kw >= 0", name="ck_sessions_requested_power_nonnegative"
        ),
        sa.CheckConstraint(
            "allocated_power_kw >= 0", name="ck_sessions_allocated_power_nonnegative"
        ),
        sa.CheckConstraint(
            "allocated_power_kw <= requested_power_kw", name="ck_sessions_allocation_within_request"
        ),
        sa.CheckConstraint("energy_consumed_kwh >= 0", name="ck_sessions_energy_nonnegative"),
        sa.CheckConstraint("solar_energy_kwh >= 0", name="ck_sessions_solar_energy_nonnegative"),
        sa.CheckConstraint("grid_energy_kwh >= 0", name="ck_sessions_grid_energy_nonnegative"),
        sa.CheckConstraint("tariff_per_kwh >= 0", name="ck_sessions_tariff_nonnegative"),
        sa.CheckConstraint("total_cost >= 0", name="ck_sessions_total_cost_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["charger_id"], ["chargers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "vehicle_id", "charger_id", "status"):
        op.create_index(op.f(f"ix_charging_sessions_{column}"), "charging_sessions", [column])

    op.create_table(
        "energy_readings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_power_kw", sa.Float(), nullable=False),
        sa.Column("allocated_power_kw", sa.Float(), nullable=False),
        sa.Column("solar_power_kw", sa.Float(), nullable=False),
        sa.Column("grid_power_kw", sa.Float(), nullable=False),
        sa.Column("interval_energy_kwh", sa.Float(), nullable=False),
        sa.Column("solar_energy_kwh", sa.Float(), nullable=False),
        sa.Column("grid_energy_kwh", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "requested_power_kw >= 0", name="ck_energy_readings_requested_nonnegative"
        ),
        sa.CheckConstraint(
            "allocated_power_kw >= 0", name="ck_energy_readings_allocated_nonnegative"
        ),
        sa.CheckConstraint(
            "allocated_power_kw <= requested_power_kw",
            name="ck_energy_readings_allocation_within_request",
        ),
        sa.CheckConstraint(
            "solar_power_kw >= 0", name="ck_energy_readings_solar_power_nonnegative"
        ),
        sa.CheckConstraint("grid_power_kw >= 0", name="ck_energy_readings_grid_power_nonnegative"),
        sa.CheckConstraint(
            "interval_energy_kwh >= 0", name="ck_energy_readings_energy_nonnegative"
        ),
        sa.CheckConstraint("solar_energy_kwh >= 0", name="ck_energy_readings_solar_nonnegative"),
        sa.CheckConstraint("grid_energy_kwh >= 0", name="ck_energy_readings_grid_nonnegative"),
        sa.ForeignKeyConstraint(["session_id"], ["charging_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_energy_readings_session_id"), "energy_readings", ["session_id"])
    op.create_index(op.f("ix_energy_readings_timestamp"), "energy_readings", ["timestamp"])

    op.create_table(
        "solar_readings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("station_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_power_kw", sa.Float(), nullable=False),
        sa.CheckConstraint("available_power_kw >= 0", name="ck_solar_readings_power_nonnegative"),
        sa.ForeignKeyConstraint(["station_id"], ["charging_stations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_solar_readings_station_id"), "solar_readings", ["station_id"])
    op.create_index(op.f("ix_solar_readings_timestamp"), "solar_readings", ["timestamp"])


def downgrade() -> None:
    op.drop_index(op.f("ix_solar_readings_timestamp"), table_name="solar_readings")
    op.drop_index(op.f("ix_solar_readings_station_id"), table_name="solar_readings")
    op.drop_table("solar_readings")
    op.drop_index(op.f("ix_energy_readings_timestamp"), table_name="energy_readings")
    op.drop_index(op.f("ix_energy_readings_session_id"), table_name="energy_readings")
    op.drop_table("energy_readings")
    for column in ("status", "charger_id", "vehicle_id", "user_id"):
        op.drop_index(op.f(f"ix_charging_sessions_{column}"), table_name="charging_sessions")
    op.drop_table("charging_sessions")
