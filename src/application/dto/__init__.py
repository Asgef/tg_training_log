"""DTO (Data Transfer Objects) для передачи данных между слоями приложения."""

from .user import UserDTO
from .machine import MachineDTO, MuscleDTO, MuscleGroupDTO
from .workout import WorkoutSessionDTO
from .set_entry import SetEntryDTO
from .input import (
    SetEntryInputDTO,
    MachineInputDTO,
    MachineUpdateInputDTO,
    RegistrationInputDTO,
    GoogleSheetsConfigInputDTO,
)
from .converters import (
    user_to_dto,
    user_from_dto,
    machine_to_dto,
    machine_from_dto,
    muscle_to_dto,
    muscle_group_to_dto,
    workout_session_to_dto,
    workout_session_from_dto,
    set_entry_to_dto,
    set_entry_from_dto,
)

__all__ = [
    "UserDTO",
    "MachineDTO",
    "MuscleDTO",
    "MuscleGroupDTO",
    "WorkoutSessionDTO",
    "SetEntryDTO",
    "SetEntryInputDTO",
    "MachineInputDTO",
    "MachineUpdateInputDTO",
    "RegistrationInputDTO",
    "GoogleSheetsConfigInputDTO",
    "user_to_dto",
    "user_from_dto",
    "machine_to_dto",
    "machine_from_dto",
    "muscle_to_dto",
    "muscle_group_to_dto",
    "workout_session_to_dto",
    "workout_session_from_dto",
    "set_entry_to_dto",
    "set_entry_from_dto",
]
