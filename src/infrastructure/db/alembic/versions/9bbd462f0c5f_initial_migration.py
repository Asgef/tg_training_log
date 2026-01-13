"""Начальная миграция

Revision ID: 9bbd462f0c5f
Revises:
Create Date: 2026-01-13 18:17:48.126684

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# идентификаторы ревизии, используемые Alembic.
revision: str = "9bbd462f0c5f"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновление схемы."""
    # ### команды автоматически сгенерированы Alembic - пожалуйста, настройте! ###
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
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("is_registered", sa.Boolean(), nullable=False),
        sa.Column("google_sheet_url", sa.Text(), nullable=True),
        sa.Column("spreadsheet_id", sa.Text(), nullable=True),
        sa.Column("telegram_username", sa.Text(), nullable=True),
        sa.Column("telegram_firstname", sa.Text(), nullable=True),
        sa.Column("telegram_lastname", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "muscles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["muscle_groups.id"],
        ),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "machine_muscles",
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("muscle_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["machines.id"],
        ),
        sa.ForeignKeyConstraint(
            ["muscle_id"],
            ["muscles.id"],
        ),
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
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["machines.id"],
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["workout_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### конец команд Alembic ###


def downgrade() -> None:
    """Откат схемы."""
    # ### команды автоматически сгенерированы Alembic - пожалуйста, настройте! ###
    op.drop_table("set_entries")
    op.drop_table("machine_muscles")
    op.drop_table("workout_sessions")
    op.drop_table("muscles")
    op.drop_table("machines")
    op.drop_table("users")
    op.drop_table("muscle_groups")
    # ### конец команд Alembic ###
