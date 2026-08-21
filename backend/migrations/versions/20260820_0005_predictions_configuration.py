"""Create demand predictions and system configuration.

Revision ID: 20260820_0005
Revises: 20260820_0004
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0005"
down_revision: str | None = "20260820_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

demand_risk_level = sa.Enum(
    "LOW", "MEDIUM", "HIGH", name="demand_risk_level", native_enum=False
)


def timestamp_column(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "demand_predictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("station_id", sa.Uuid(), nullable=False),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("prediction_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_demand_kw", sa.Float(), nullable=False),
        sa.Column("capacity_kw", sa.Float(), nullable=False),
        sa.Column("risk_level", demand_risk_level, nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.CheckConstraint(
            "predicted_demand_kw >= 0", name="ck_predictions_demand_nonnegative"
        ),
        sa.CheckConstraint("capacity_kw > 0", name="ck_predictions_capacity_positive"),
        sa.CheckConstraint("prediction_for > generated_at", name="ck_predictions_future_target"),
        sa.ForeignKeyConstraint(
            ["station_id"], ["charging_stations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_demand_predictions_station_id"), "demand_predictions", ["station_id"]
    )
    op.create_index(
        op.f("ix_demand_predictions_generated_at"), "demand_predictions", ["generated_at"]
    )

    op.create_table(
        "system_configurations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("singleton_key", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("simulation_speed", sa.Integer(), nullable=False),
        sa.Column("grid_emission_factor_kg_per_kwh", sa.Float(), nullable=False),
        sa.Column("high_demand_threshold", sa.Float(), nullable=False),
        sa.Column("medium_peak_threshold", sa.Float(), nullable=False),
        sa.Column("high_peak_threshold", sa.Float(), nullable=False),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint("simulation_speed > 0", name="ck_config_simulation_speed_positive"),
        sa.CheckConstraint(
            "grid_emission_factor_kg_per_kwh >= 0", name="ck_config_emission_nonnegative"
        ),
        sa.CheckConstraint(
            "high_demand_threshold > 0 AND high_demand_threshold <= 1",
            name="ck_config_high_demand_range",
        ),
        sa.CheckConstraint(
            "medium_peak_threshold > 0 AND medium_peak_threshold < high_peak_threshold "
            "AND high_peak_threshold <= 1",
            name="ck_config_peak_threshold_order",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("singleton_key"),
    )


def downgrade() -> None:
    op.drop_table("system_configurations")
    op.drop_index(op.f("ix_demand_predictions_generated_at"), table_name="demand_predictions")
    op.drop_index(op.f("ix_demand_predictions_station_id"), table_name="demand_predictions")
    op.drop_table("demand_predictions")
