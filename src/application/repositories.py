from abc import ABC, abstractmethod
from typing import List, Optional, Any

# Импорт доменных моделей
from src.domain.models import (
    User,
    Machine,
    WorkoutSession,
    SetEntry,
    Muscle,
    MuscleGroup,
)


class BaseRepository(ABC):
    @abstractmethod
    async def get_by_id(self, item_id: Any) -> Optional[Any]:
        pass

    @abstractmethod
    async def add(self, item: Any) -> Any:
        pass

    @abstractmethod
    async def update(self, item: Any) -> Any:
        pass

    @abstractmethod
    async def delete(self, item_id: Any) -> None:
        pass


class IUserRepository(BaseRepository):
    @abstractmethod
    async def get_by_telegram_id(
        self, telegram_id: int
    ) -> Optional["User"]:  # Прямая ссылка
        pass

    @abstractmethod
    async def get_admin_approved_users(self) -> List["User"]:
        pass

    @abstractmethod
    async def save_google_sheet_config(
        self, user_id: int, url: str, spreadsheet_id: str
    ) -> None:
        pass


class IMachineRepository(BaseRepository):
    @abstractmethod
    async def get_user_machines(
        self, user_id: int, include_archived: bool = False
    ) -> List["Machine"]:
        pass

    @abstractmethod
    async def get_user_machine_by_name(
        self, user_id: int, name: str
    ) -> Optional["Machine"]:
        pass

    @abstractmethod
    async def add_machine_with_muscles(
        self, machine: "Machine", muscle_ids: List[int]
    ) -> "Machine":
        pass


class IWorkoutSessionRepository(BaseRepository):
    @abstractmethod
    async def get_active_session_for_user(
        self, user_id: int
    ) -> Optional["WorkoutSession"]:
        pass

    @abstractmethod
    async def start_session(self, user_id: int) -> "WorkoutSession":
        pass

    @abstractmethod
    async def end_session(self, session_id: int) -> None:
        pass


class ISetEntryRepository(BaseRepository):
    @abstractmethod
    async def add_set_entry(self, set_entry: "SetEntry") -> "SetEntry":
        pass


class IMuscleRepository(BaseRepository):
    @abstractmethod
    async def get_all_muscles(self) -> List["Muscle"]:
        pass

    @abstractmethod
    async def get_muscles_by_ids(self, muscle_ids: List[int]) -> List["Muscle"]:
        pass


class IMuscleGroupRepository(BaseRepository):
    @abstractmethod
    async def get_all_muscle_groups(self) -> List["MuscleGroup"]:
        pass
