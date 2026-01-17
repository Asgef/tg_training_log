"""merge heads

Revision ID: 0223cc9e7784
Revises: c1d2e3f4a5b6, d4e5f6a7b8c9
Create Date: 2026-01-17 19:48:24.221469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# идентификаторы ревизии, используемые Alembic.
revision: str = '0223cc9e7784'
down_revision: Union[str, Sequence[str], None] = ('c1d2e3f4a5b6', 'd4e5f6a7b8c9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновление схемы."""
    pass


def downgrade() -> None:
    """Откат схемы."""
    pass
