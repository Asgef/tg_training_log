"""add rir to set_entries

Revision ID: d4e5f6a7b8c9
Revises: 4c3b6f8a2d12
Create Date: 2026-01-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# идентификаторы ревизии, используемые Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "4c3b6f8a2d12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновление схемы."""
    with op.batch_alter_table("set_entries") as batch_op:
        batch_op.add_column(sa.Column("rir", sa.Integer(), nullable=False, server_default="2"))
        batch_op.create_check_constraint("ck_set_entries_rir_range", "rir >= 0 AND rir <= 5")
        batch_op.drop_column("is_failure")
        batch_op.alter_column("rir", server_default=None)


def downgrade() -> None:
    """Откат схемы."""
    with op.batch_alter_table("set_entries") as batch_op:
        batch_op.add_column(sa.Column("is_failure", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.drop_constraint("ck_set_entries_rir_range", type_="check")
        batch_op.drop_column("rir")
