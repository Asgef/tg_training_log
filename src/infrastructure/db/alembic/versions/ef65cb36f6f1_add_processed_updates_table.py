"""add_processed_updates_table

Revision ID: ef65cb36f6f1
Revises: 9bbd462f0c5f
Create Date: 2026-01-14 15:43:16.486330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# идентификаторы ревизии, используемые Alembic.
revision: str = 'ef65cb36f6f1'
down_revision: Union[str, Sequence[str], None] = '9bbd462f0c5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновление схемы."""
    op.create_table(
        "processed_updates",
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("update_id"),
    )
    # Создаём индекс для быстрого поиска по processed_at (для cleanup)
    op.create_index(
        "ix_processed_updates_processed_at",
        "processed_updates",
        ["processed_at"],
    )


def downgrade() -> None:
    """Откат схемы."""
    op.drop_index("ix_processed_updates_processed_at", table_name="processed_updates")
    op.drop_table("processed_updates")
