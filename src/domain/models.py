# src/domain/models.py
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship, validates
from sqlalchemy import BigInteger, Boolean, Text, Integer, Numeric, TIMESTAMP, ForeignKey
from typing import List
from datetime import datetime, timezone

Base = declarative_base()

# Константы для валидации
MAX_NAME_LENGTH = 255
MIN_WEIGHT = 0.01
MIN_REPS = 1


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    google_sheet_url: Mapped[str | None] = mapped_column(Text)
    spreadsheet_id: Mapped[str | None] = mapped_column(Text)
    last_exported_set_id: Mapped[int | None] = mapped_column(Integer)
    telegram_username: Mapped[str | None] = mapped_column(Text)
    telegram_firstname: Mapped[str | None] = mapped_column(Text)
    telegram_lastname: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
    timezone: Mapped[str] = mapped_column(Text, default="Europe/Moscow")


class MuscleZone(Base):
    __tablename__ = "muscle_zones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    muscles: Mapped[List["Muscle"]] = relationship(
        "Muscle", secondary="muscle_zone_muscles", back_populates="zones", lazy="selectin"
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        """Валидация названия зоны."""
        if not value or not value.strip():
            raise ValueError("Название зоны не может быть пустым")
        if len(value.strip()) > MAX_NAME_LENGTH:
            raise ValueError(f"Название зоны не может быть длиннее {MAX_NAME_LENGTH} символов")
        return value.strip()


class Muscle(Base):
    __tablename__ = "muscles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    zones: Mapped[List["MuscleZone"]] = relationship(
        "MuscleZone", secondary="muscle_zone_muscles", back_populates="muscles", lazy="selectin"
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        """Валидация названия мышцы."""
        if not value or not value.strip():
            raise ValueError("Название мышцы не может быть пустым")
        if len(value.strip()) > MAX_NAME_LENGTH:
            raise ValueError(f"Название мышцы не может быть длиннее {MAX_NAME_LENGTH} символов")
        return value.strip()


class MuscleZoneMuscle(Base):
    __tablename__ = "muscle_zone_muscles"
    zone_id: Mapped[int] = mapped_column(ForeignKey("muscle_zones.id"), primary_key=True)
    muscle_id: Mapped[int] = mapped_column(ForeignKey("muscles.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class Machine(Base):
    __tablename__ = "machines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    muscles: Mapped[List["Muscle"]] = relationship(
        "Muscle", secondary="machine_muscles", backref="machines", lazy="selectin"
    )
    zones: Mapped[List["MuscleZone"]] = relationship(
        "MuscleZone", secondary="machine_zones", backref="machines", lazy="selectin"
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        """Валидация названия тренажёра."""
        if not value or not value.strip():
            raise ValueError("Название тренажёра не может быть пустым")
        if len(value.strip()) > MAX_NAME_LENGTH:
            raise ValueError(f"Название тренажёра не может быть длиннее {MAX_NAME_LENGTH} символов")
        return value.strip()


class MachineMuscle(Base):
    __tablename__ = "machine_muscles"
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), primary_key=True)
    muscle_id: Mapped[int] = mapped_column(ForeignKey("muscles.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class MachineZone(Base):
    __tablename__ = "machine_zones"
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("muscle_zones.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class SetEntry(Base):
    __tablename__ = "set_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"))
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"))
    weight: Mapped[float] = mapped_column(Numeric(6, 2))
    reps: Mapped[int] = mapped_column(Integer)
    is_failure: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    zones: Mapped[List["MuscleZone"]] = relationship(
        "MuscleZone", secondary="set_entry_zones", backref="set_entries", lazy="selectin"
    )
    muscles: Mapped[List["Muscle"]] = relationship(
        "Muscle", secondary="set_entry_muscles", backref="set_entries", lazy="selectin"
    )

    @validates("weight")
    def validate_weight(self, key: str, value: float) -> float:
        """Валидация веса подхода."""
        if value <= 0:
            raise ValueError(f"Вес должен быть больше {MIN_WEIGHT}")
        return value

    @validates("reps")
    def validate_reps(self, key: str, value: int) -> int:
        """Валидация количества повторений."""
        if value < MIN_REPS:
            raise ValueError(f"Количество повторений должно быть не меньше {MIN_REPS}")
        return value


class SetEntryZone(Base):
    __tablename__ = "set_entry_zones"
    set_entry_id: Mapped[int] = mapped_column(ForeignKey("set_entries.id"), primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("muscle_zones.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class SetEntryMuscle(Base):
    __tablename__ = "set_entry_muscles"
    set_entry_id: Mapped[int] = mapped_column(ForeignKey("set_entries.id"), primary_key=True)
    muscle_id: Mapped[int] = mapped_column(ForeignKey("muscles.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class ProcessedUpdate(Base):
    """Модель для хранения обработанных Telegram updates для обеспечения идемпотентности."""
    __tablename__ = "processed_updates"
    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
