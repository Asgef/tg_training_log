"""Конвертеры для преобразования между domain моделями и DTO."""
from typing import Optional, List
from src.domain.models import (
    User,
    Machine,
    Muscle,
    MuscleZone,
    WorkoutSession,
    SetEntry,
)
from .user import UserDTO
from .machine import MachineDTO, MuscleDTO, MuscleZoneDTO
from .workout import WorkoutSessionDTO
from .set_entry import SetEntryDTO


def user_to_dto(user: User) -> UserDTO:
    """Конвертирует domain модель User в UserDTO."""
    return UserDTO(
        id=user.id,
        telegram_id=user.telegram_id,
        is_registered=user.is_registered,
        google_sheet_url=user.google_sheet_url,
        spreadsheet_id=user.spreadsheet_id,
        telegram_username=user.telegram_username,
        telegram_firstname=user.telegram_firstname,
        telegram_lastname=user.telegram_lastname,
        created_at=user.created_at,
        updated_at=user.updated_at,
        timezone=user.timezone,
    )


def user_from_dto(dto: UserDTO) -> User:
    """Создаёт domain модель User из UserDTO.
    
    Внимание: Этот метод создаёт новый объект User, но не сохраняет его в БД.
    Для сохранения используйте репозиторий.
    """
    user = User()
    user.id = dto.id
    user.telegram_id = dto.telegram_id if dto.telegram_id is not None else dto.id
    user.is_registered = dto.is_registered
    user.google_sheet_url = dto.google_sheet_url
    user.spreadsheet_id = dto.spreadsheet_id
    user.telegram_username = dto.telegram_username
    user.telegram_firstname = dto.telegram_firstname
    user.telegram_lastname = dto.telegram_lastname
    user.created_at = dto.created_at
    user.updated_at = dto.updated_at
    user.timezone = dto.timezone
    return user


def muscle_zone_to_dto(muscle_zone: MuscleZone) -> MuscleZoneDTO:
    """Конвертирует domain модель MuscleZone в MuscleZoneDTO."""
    return MuscleZoneDTO(
        id=muscle_zone.id,
        name=muscle_zone.name,
        created_at=muscle_zone.created_at,
        updated_at=muscle_zone.updated_at,
    )


def muscle_to_dto(muscle: Muscle) -> MuscleDTO:
    """Конвертирует domain модель Muscle в MuscleDTO."""
    zones_dto = [muscle_zone_to_dto(zone) for zone in muscle.zones] if muscle.zones else []
    return MuscleDTO(
        id=muscle.id,
        name=muscle.name,
        zones=zones_dto,
        created_at=muscle.created_at,
        updated_at=muscle.updated_at,
    )


def machine_to_dto(machine: Machine) -> MachineDTO:
    """Конвертирует domain модель Machine в MachineDTO."""
    muscles_dto = [muscle_to_dto(muscle) for muscle in machine.muscles]
    zones_dto = [muscle_zone_to_dto(zone) for zone in machine.zones]
    
    return MachineDTO(
        id=machine.id,
        user_id=machine.user_id,
        name=machine.name,
        photo_file_id=machine.photo_file_id,
        is_archived=machine.is_archived,
        zones=zones_dto,
        muscles=muscles_dto,
        created_at=machine.created_at,
        updated_at=machine.updated_at,
    )


def machine_from_dto(dto: MachineDTO) -> Machine:
    """Создаёт domain модель Machine из MachineDTO.
    
    Внимание: Этот метод создаёт новый объект Machine, но не сохраняет его в БД.
    Для сохранения используйте репозиторий. Связи с мышцами нужно устанавливать отдельно.
    """
    machine = Machine()
    machine.id = dto.id
    machine.user_id = dto.user_id
    machine.name = dto.name
    machine.photo_file_id = dto.photo_file_id
    machine.is_archived = dto.is_archived
    machine.created_at = dto.created_at
    machine.updated_at = dto.updated_at
    # Мышцы нужно устанавливать отдельно через relationship
    return machine


def workout_session_to_dto(session: WorkoutSession) -> WorkoutSessionDTO:
    """Конвертирует domain модель WorkoutSession в WorkoutSessionDTO."""
    return WorkoutSessionDTO(
        id=session.id,
        user_id=session.user_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def workout_session_from_dto(dto: WorkoutSessionDTO) -> WorkoutSession:
    """Создаёт domain модель WorkoutSession из WorkoutSessionDTO.
    
    Внимание: Этот метод создаёт новый объект WorkoutSession, но не сохраняет его в БД.
    Для сохранения используйте репозиторий.
    """
    session = WorkoutSession()
    session.id = dto.id
    session.user_id = dto.user_id
    session.started_at = dto.started_at
    session.ended_at = dto.ended_at
    session.created_at = dto.created_at
    session.updated_at = dto.updated_at
    return session


def set_entry_to_dto(set_entry: SetEntry) -> SetEntryDTO:
    """Конвертирует domain модель SetEntry в SetEntryDTO."""
    return SetEntryDTO(
        id=set_entry.id,
        session_id=set_entry.session_id,
        machine_id=set_entry.machine_id,
        weight=float(set_entry.weight),
        reps=set_entry.reps,
        is_failure=set_entry.is_failure,
        created_at=set_entry.created_at,
        updated_at=set_entry.updated_at,
    )


def set_entry_from_dto(dto: SetEntryDTO) -> SetEntry:
    """Создаёт domain модель SetEntry из SetEntryDTO.
    
    Внимание: Этот метод создаёт новый объект SetEntry, но не сохраняет его в БД.
    Для сохранения используйте репозиторий.
    """
    set_entry = SetEntry()
    set_entry.id = dto.id
    set_entry.session_id = dto.session_id
    set_entry.machine_id = dto.machine_id
    set_entry.weight = dto.weight
    set_entry.reps = dto.reps
    set_entry.is_failure = dto.is_failure
    set_entry.created_at = dto.created_at
    set_entry.updated_at = dto.updated_at
    return set_entry
