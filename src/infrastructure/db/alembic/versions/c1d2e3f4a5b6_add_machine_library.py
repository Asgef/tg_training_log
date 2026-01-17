"""add_machine_library

Revision ID: c1d2e3f4a5b6
Revises: b7b3e8d0c1a2
Create Date: 2026-01-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# идентификаторы ревизии, используемые Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b7b3e8d0c1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновление схемы."""
    op.create_table(
        "machine_library",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name_ru", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name_ru"),
    )
    op.create_index("ix_machine_library_name_ru", "machine_library", ["name_ru"], unique=True)
    op.create_index("ix_machine_library_created_at", "machine_library", ["created_at"])

    op.create_table(
        "machine_library_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("machine_library_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["machine_library_id"], ["machine_library.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias"),
    )
    op.create_index(
        "ix_machine_library_aliases_machine_library_id",
        "machine_library_aliases",
        ["machine_library_id"],
    )
    op.create_index(
        "ix_machine_library_aliases_alias",
        "machine_library_aliases",
        ["alias"],
        unique=True,
    )

    op.create_table(
        "machine_library_zones",
        sa.Column("machine_library_id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["machine_library_id"], ["machine_library.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["zone_id"], ["muscle_zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("machine_library_id", "zone_id"),
    )
    op.create_index(
        "ix_machine_library_zones_machine_library_id",
        "machine_library_zones",
        ["machine_library_id"],
    )
    op.create_index(
        "ix_machine_library_zones_zone_id",
        "machine_library_zones",
        ["zone_id"],
    )

    op.create_table(
        "machine_library_muscles",
        sa.Column("machine_library_id", sa.Integer(), nullable=False),
        sa.Column("muscle_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["machine_library_id"], ["machine_library.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("machine_library_id", "muscle_id"),
    )
    op.create_index(
        "ix_machine_library_muscles_machine_library_id",
        "machine_library_muscles",
        ["machine_library_id"],
    )
    op.create_index(
        "ix_machine_library_muscles_muscle_id",
        "machine_library_muscles",
        ["muscle_id"],
    )

    op.add_column(
        "machines", sa.Column("library_machine_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        "ix_machines_library_machine_id", "machines", ["library_machine_id"]
    )
    op.create_foreign_key(
        "fk_machines_library_machine_id",
        "machines",
        "machine_library",
        ["library_machine_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Откат схемы."""
    op.drop_constraint(
        "fk_machines_library_machine_id", "machines", type_="foreignkey"
    )
    op.drop_index("ix_machines_library_machine_id", table_name="machines")
    op.drop_column("machines", "library_machine_id")

    op.drop_index(
        "ix_machine_library_muscles_muscle_id", table_name="machine_library_muscles"
    )
    op.drop_index(
        "ix_machine_library_muscles_machine_library_id",
        table_name="machine_library_muscles",
    )
    op.drop_table("machine_library_muscles")

    op.drop_index(
        "ix_machine_library_zones_zone_id", table_name="machine_library_zones"
    )
    op.drop_index(
        "ix_machine_library_zones_machine_library_id",
        table_name="machine_library_zones",
    )
    op.drop_table("machine_library_zones")

    op.drop_index(
        "ix_machine_library_aliases_alias", table_name="machine_library_aliases"
    )
    op.drop_index(
        "ix_machine_library_aliases_machine_library_id",
        table_name="machine_library_aliases",
    )
    op.drop_table("machine_library_aliases")

    op.drop_index("ix_machine_library_created_at", table_name="machine_library")
    op.drop_index("ix_machine_library_name_ru", table_name="machine_library")
    op.drop_table("machine_library")
