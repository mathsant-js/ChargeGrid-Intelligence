"""Create tariffs, invoices, and alerts.

Revision ID: 20260820_0004
Revises: 20260818_0003
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0004"
down_revision: str | None = "20260818_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

invoice_status = sa.Enum("OPEN", "CLOSED", "CANCELLED", name="invoice_status", native_enum=False)
alert_type = sa.Enum(
    "HIGH_DEMAND", "PEAK_RISK", "HIGH_SOLAR_AVAILABILITY", "SESSION_FINISHED",
    name="alert_type", native_enum=False,
)
alert_severity = sa.Enum("INFO", "WARNING", "CRITICAL", name="alert_severity", native_enum=False)


def created_at_column() -> sa.Column[object]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "tariffs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("price_per_kwh", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BRL", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        created_at_column(),
        sa.CheckConstraint("price_per_kwh >= 0", name="ck_tariffs_price_nonnegative"),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from", name="ck_tariffs_valid_period"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tariffs_is_active"), "tariffs", ["is_active"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("energy_kwh", sa.Numeric(14, 4), nullable=False),
        sa.Column("tariff_per_kwh", sa.Numeric(12, 4), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", invoice_status, nullable=False),
        created_at_column(),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("energy_kwh >= 0", name="ck_invoices_energy_nonnegative"),
        sa.CheckConstraint("tariff_per_kwh >= 0", name="ck_invoices_tariff_nonnegative"),
        sa.CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_nonnegative"),
        sa.CheckConstraint("total >= 0", name="ck_invoices_total_nonnegative"),
        sa.ForeignKeyConstraint(["session_id"], ["charging_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(op.f("ix_invoices_user_id"), "invoices", ["user_id"])
    op.create_index(op.f("ix_invoices_status"), "invoices", ["status"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("station_id", sa.Uuid(), nullable=False),
        sa.Column("type", alert_type, nullable=False),
        sa.Column("severity", alert_severity, nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        created_at_column(),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["station_id"], ["charging_stations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("station_id", "type", "severity", "created_at"):
        op.create_index(op.f(f"ix_alerts_{column}"), "alerts", [column])


def downgrade() -> None:
    for column in ("created_at", "severity", "type", "station_id"):
        op.drop_index(op.f(f"ix_alerts_{column}"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_index(op.f("ix_invoices_status"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_user_id"), table_name="invoices")
    op.drop_table("invoices")
    op.drop_index(op.f("ix_tariffs_is_active"), table_name="tariffs")
    op.drop_table("tariffs")
