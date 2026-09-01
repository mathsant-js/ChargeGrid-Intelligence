"""Prevent concurrent active sessions for the same charger or vehicle.

Revision ID: 20260901_0008
Revises: 20260831_0007
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0008"
down_revision: str | None = "20260831_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_SESSION_PREDICATE = sa.text("status IN ('CREATED', 'CHARGING', 'PAUSED')")


def upgrade() -> None:
    op.create_index(
        "uq_charging_sessions_active_charger",
        "charging_sessions",
        ["charger_id"],
        unique=True,
        postgresql_where=ACTIVE_SESSION_PREDICATE,
    )
    op.create_index(
        "uq_charging_sessions_active_vehicle",
        "charging_sessions",
        ["vehicle_id"],
        unique=True,
        postgresql_where=ACTIVE_SESSION_PREDICATE,
    )


def downgrade() -> None:
    op.drop_index("uq_charging_sessions_active_vehicle", table_name="charging_sessions")
    op.drop_index("uq_charging_sessions_active_charger", table_name="charging_sessions")
