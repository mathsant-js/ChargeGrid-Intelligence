"""Keep at most one active default tariff.

Revision ID: 20260916_0011
Revises: 20260916_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260916_0011"
down_revision: str | None = "20260916_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    tariffs = sa.table(
        "tariffs",
        sa.column("id", sa.Uuid()),
        sa.column("is_active", sa.Boolean()),
        sa.column("valid_from", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    active_ids = connection.execute(
        sa.select(tariffs.c.id)
        .where(tariffs.c.is_active.is_(True))
        .order_by(tariffs.c.valid_from.desc(), tariffs.c.created_at.desc(), tariffs.c.id.desc())
    ).scalars().all()
    if len(active_ids) > 1:
        connection.execute(
            sa.update(tariffs).where(tariffs.c.id.in_(active_ids[1:])).values(is_active=False)
        )
    op.create_index(
        "uq_tariffs_one_active", "tariffs", ["is_active"], unique=True,
        postgresql_where=sa.text("is_active"), sqlite_where=sa.text("is_active = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_tariffs_one_active", table_name="tariffs")
