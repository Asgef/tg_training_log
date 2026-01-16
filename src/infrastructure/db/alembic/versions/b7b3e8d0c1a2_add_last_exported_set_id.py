"""add_last_exported_set_id

Revision ID: b7b3e8d0c1a2
Revises: 4c3b6f8a2d12
Create Date: 2026-01-16 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# идентификаторы ревизии, используемые Alembic.
revision: str = "b7b3e8d0c1a2"
down_revision: Union[str, Sequence[str], None] = "4c3b6f8a2d12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновление схемы."""
    op.add_column("users", sa.Column("last_exported_set_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_users_last_exported_set_id", "users", ["last_exported_set_id"]
    )


def downgrade() -> None:
    """Откат схемы."""
    op.drop_index("ix_users_last_exported_set_id", table_name="users")
    op.drop_column("users", "last_exported_set_id")
