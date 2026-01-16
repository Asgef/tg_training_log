"""refactor schema v2

Revision ID: 4c3b6f8a2d12
Revises: ef65cb36f6f1
Create Date: 2026-01-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# идентификаторы ревизии, используемые Alembic.
revision: str = "4c3b6f8a2d12"
down_revision: Union[str, Sequence[str], None] = "ef65cb36f6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновление схемы."""
    # users: добавляем telegram_id и индексы
    op.add_column("users", sa.Column("telegram_id", sa.BigInteger(), nullable=True))
    op.execute("UPDATE users SET telegram_id = id WHERE telegram_id IS NULL")
    op.alter_column("users", "telegram_id", nullable=False)
    op.create_unique_constraint("uq_users_telegram_id", "users", ["telegram_id"])
    op.create_index("ix_users_is_registered", "users", ["is_registered"])
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.alter_column(
        "users",
        "timezone",
        existing_type=sa.Text(),
        server_default="Europe/Moscow",
    )

    # удаляем старые таблицы (кроме users и processed_updates)
    op.drop_table("set_entries")
    op.drop_table("machine_muscles")
    op.drop_table("workout_sessions")
    op.drop_table("muscles")
    op.drop_table("machines")
    op.drop_table("muscle_groups")

    # новые справочники
    op.create_table(
        "muscle_zones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_muscle_zones_name", "muscle_zones", ["name"], unique=True)

    op.create_table(
        "muscles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_muscles_name", "muscles", ["name"], unique=True)

    op.create_table(
        "muscle_zone_muscles",
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("muscle_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["muscle_zones.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("zone_id", "muscle_id"),
    )
    op.create_index("ix_muscle_zone_muscles_zone_id", "muscle_zone_muscles", ["zone_id"])
    op.create_index("ix_muscle_zone_muscles_muscle_id", "muscle_zone_muscles", ["muscle_id"])

    # machines
    op.create_table(
        "machines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("photo_file_id", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_machines_user_id", "machines", ["user_id"])
    op.create_index("ix_machines_is_archived", "machines", ["is_archived"])
    op.create_index("ix_machines_created_at", "machines", ["created_at"])

    op.create_table(
        "machine_zones",
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["muscle_zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("machine_id", "zone_id"),
    )
    op.create_index("ix_machine_zones_machine_id", "machine_zones", ["machine_id"])
    op.create_index("ix_machine_zones_zone_id", "machine_zones", ["zone_id"])

    op.create_table(
        "machine_muscles",
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("muscle_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("machine_id", "muscle_id"),
    )
    op.create_index("ix_machine_muscles_machine_id", "machine_muscles", ["machine_id"])
    op.create_index("ix_machine_muscles_muscle_id", "machine_muscles", ["muscle_id"])

    # sessions
    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workout_sessions_user_id", "workout_sessions", ["user_id"])
    op.create_index("ix_workout_sessions_started_at", "workout_sessions", ["started_at"])
    op.create_index("ix_workout_sessions_ended_at", "workout_sessions", ["ended_at"])

    # set entries
    op.create_table(
        "set_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("is_failure", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["workout_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_set_entries_session_id", "set_entries", ["session_id"])
    op.create_index("ix_set_entries_machine_id", "set_entries", ["machine_id"])
    op.create_index("ix_set_entries_created_at", "set_entries", ["created_at"])

    # snapshot tables
    op.create_table(
        "set_entry_zones",
        sa.Column("set_entry_id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["set_entry_id"], ["set_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["muscle_zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("set_entry_id", "zone_id"),
    )
    op.create_index("ix_set_entry_zones_set_entry_id", "set_entry_zones", ["set_entry_id"])
    op.create_index("ix_set_entry_zones_zone_id", "set_entry_zones", ["zone_id"])

    op.create_table(
        "set_entry_muscles",
        sa.Column("set_entry_id", sa.Integer(), nullable=False),
        sa.Column("muscle_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["set_entry_id"], ["set_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("set_entry_id", "muscle_id"),
    )
    op.create_index("ix_set_entry_muscles_set_entry_id", "set_entry_muscles", ["set_entry_id"])
    op.create_index("ix_set_entry_muscles_muscle_id", "set_entry_muscles", ["muscle_id"])


def downgrade() -> None:
    """Откат схемы."""
    op.drop_table("set_entry_muscles")
    op.drop_table("set_entry_zones")
    op.drop_table("set_entries")
    op.drop_table("workout_sessions")
    op.drop_table("machine_muscles")
    op.drop_table("machine_zones")
    op.drop_table("machines")
    op.drop_table("muscle_zone_muscles")
    op.drop_table("muscles")
    op.drop_table("muscle_zones")

    # откат users
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_is_registered", table_name="users")
    op.drop_constraint("uq_users_telegram_id", "users", type_="unique")
    op.drop_column("users", "telegram_id")
    op.alter_column(
        "users",
        "timezone",
        existing_type=sa.Text(),
        server_default="Europe/Berlin",
    )

    # старые таблицы
    op.create_table(
        "muscle_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "machines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("photo_file_id", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "muscles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["muscle_groups.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "machine_muscles",
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("muscle_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
        sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"]),
        sa.PrimaryKeyConstraint("machine_id", "muscle_id"),
    )
    op.create_table(
        "set_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("failure", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["workout_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
