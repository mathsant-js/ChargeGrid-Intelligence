"""Enforce valid user roles and charger statuses.

Revision ID: 20260831_0006
Revises: 20260820_0005
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260831_0006"
down_revision: str | None = "20260820_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint("user_role", "users", "role IN ('ADMIN', 'USER')")
    op.create_check_constraint(
        "charger_status",
        "chargers",
        "status IN ('AVAILABLE', 'CHARGING', 'UNAVAILABLE')",
    )


def downgrade() -> None:
    op.drop_constraint("charger_status", "chargers", type_="check")
    op.drop_constraint("user_role", "users", type_="check")
