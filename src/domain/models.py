# src/domain/models.py
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Boolean, Text, Integer, Numeric, TIMESTAMP, ForeignKey
from typing import List
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    google_sheet_url: Mapped[str | None] = mapped_column(Text)
    spreadsheet_id: Mapped[str | None] = mapped_column(Text)
    telegram_username: Mapped[str | None] = mapped_column(Text)
    telegram_firstname: Mapped[str | None] = mapped_column(Text)
    telegram_lastname: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    timezone: Mapped[str] = mapped_column(Text, default="Europe/Berlin")


class MuscleGroup(Base):
    __tablename__ = "muscle_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Muscle(Base):
    __tablename__ = "muscles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("muscle_groups.id"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    group: Mapped["MuscleGroup"] = relationship(
        "MuscleGroup", backref="muscles", lazy="selectin"
    )


class Machine(Base):
    __tablename__ = "machines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    muscles: Mapped[List["Muscle"]] = relationship(
        "Muscle", secondary="machine_muscles", backref="machines", lazy="selectin"
    )


class MachineMuscle(Base):
    __tablename__ = "machine_muscles"
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), primary_key=True)
    muscle_id: Mapped[int] = mapped_column(ForeignKey("muscles.id"), primary_key=True)


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SetEntry(Base):
    __tablename__ = "set_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"))
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"))
    weight: Mapped[float] = mapped_column(Numeric(5, 2))
    reps: Mapped[int] = mapped_column(Integer)
    failure: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
