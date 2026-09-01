"""Enforce valid charging session statuses.

Revision ID: 20260831_0007
Revises: 20260831_0006
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260831_0007"
down_revision: str | None = "20260831_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "charging_session_status",
        "charging_sessions",
        "status IN ('CREATED', 'CHARGING', 'PAUSED', 'COMPLETED', 'CANCELLED')",
    )


def downgrade() -> None:
    op.drop_constraint("charging_session_status", "charging_sessions", type_="check")
