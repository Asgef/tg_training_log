from abc import ABC, abstractmethod
from typing import List, Optional, Any

# Импорт доменных моделей
from src.domain.models import (
    User,
    Machine,
    WorkoutSession,
    SetEntry,
    Muscle,
    MuscleZone,
    ProcessedUpdate,
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
    async def add_machine_with_tags(
        self, machine: "Machine", zone_ids: List[int], muscle_ids: List[int]
    ) -> "Machine":
        pass

    @abstractmethod
    async def update_machine_muscles(
        self, machine_id: int, muscle_ids: List[int]
    ) -> None:
        pass

    @abstractmethod
    async def update_machine_zones(
        self, machine_id: int, zone_ids: List[int]
    ) -> None:
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

    @abstractmethod
    async def add_set_entry_snapshots(
        self, set_entry_id: int, zone_ids: List[int], muscle_ids: List[int]
    ) -> None:
        """Добавляет snapshot зон и мышц для подхода."""
        pass

    @abstractmethod
    async def get_recent_machine_ids(self, user_id: int, limit: int = 5) -> List[int]:
        """Возвращает последние использованные тренажёры пользователя."""
        pass

    @abstractmethod
    async def get_last_set_for_machine(
        self, user_id: int, machine_id: int
    ) -> Optional["SetEntry"]:
        """Возвращает последний подход пользователя по тренажёру."""
        pass

    @abstractmethod
    async def has_entries_for_session(self, session_id: int) -> bool:
        """Проверяет, есть ли подходы у тренировки."""
        pass

    @abstractmethod
    async def delete_by_session_id(self, session_id: int) -> int:
        """Удаляет все подходы по ID тренировки, возвращает количество удалённых."""
        pass


class IMuscleRepository(BaseRepository):
    @abstractmethod
    async def get_all_muscles(self) -> List["Muscle"]:
        pass

    @abstractmethod
    async def get_muscles_by_ids(self, muscle_ids: List[int]) -> List["Muscle"]:
        pass

    @abstractmethod
    async def get_muscles_by_zone_id(self, zone_id: int) -> List["Muscle"]:
        pass


class IMuscleZoneRepository(BaseRepository):
    @abstractmethod
    async def get_all_muscle_zones(self) -> List["MuscleZone"]:
        pass

    @abstractmethod
    async def get_muscle_zone_by_id(self, zone_id: int) -> Optional["MuscleZone"]:
        pass

    @abstractmethod
    async def get_muscle_zones_by_ids(self, zone_ids: List[int]) -> List["MuscleZone"]:
        pass


class IProcessedUpdateRepository(ABC):
    """Репозиторий для работы с обработанными Telegram updates."""
    
    @abstractmethod
    async def is_processed(self, update_id: int) -> bool:
        """Проверяет, был ли update уже обработан.
        
        Args:
            update_id: ID Telegram update
            
        Returns:
            True если update уже обработан, False иначе
        """
        pass
    
    @abstractmethod
    async def mark_as_processed(self, update_id: int) -> None:
        """Помечает update как обработанный.
        
        Args:
            update_id: ID Telegram update
        """
        pass
    
    @abstractmethod
    async def cleanup_old_updates(self, hours: int = 24) -> int:
        """Удаляет старые записи о processed updates.
        
        Args:
            hours: Количество часов, после которых записи считаются старыми (по умолчанию 24)
            
        Returns:
            Количество удалённых записей
        """
        pass
