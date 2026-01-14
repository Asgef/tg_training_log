from abc import ABC, abstractmethod
from typing import Optional, List

# Импорт доменных моделей
from src.domain.models import User, Machine, WorkoutSession, SetEntry


class IRegistrationUseCase(ABC):
    @abstractmethod
    async def request_registration(
        self,
        telegram_id: int,
        username: str,
        first_name: str,
        last_name: str,
        description: str,
    ) -> bool:
        """Обрабатывает запрос на регистрацию пользователя."""
        pass

    @abstractmethod
    async def approve_registration(self, user_id: int) -> bool:
        """Одобряет регистрацию пользователя."""
        pass

    @abstractmethod
    async def reject_registration(self, user_id: int) -> bool:
        """Отклоняет регистрацию пользователя."""
        pass


class IWorkoutUseCase(ABC):
    @abstractmethod
    async def start_new_workout(self, user_id: int) -> Optional["WorkoutSession"]:
        """Начинает новую тренировку для пользователя."""
        pass

    @abstractmethod
    async def end_current_workout(self, user_id: int) -> Optional["WorkoutSession"]:
        """Завершает текущую активную тренировку пользователя."""
        pass

    @abstractmethod
    async def record_set(
        self, user_id: int, machine_id: int, weight: float, reps: int, failure: bool
    ) -> Optional["SetEntry"]:
        """Записывает подход для активной тренировки."""
        pass

    @abstractmethod
    async def get_active_workout_session(
        self, user_id: int
    ) -> Optional["WorkoutSession"]:
        """Получает активную тренировку пользователя."""
        pass


class IMachineManagementUseCase(ABC):
    @abstractmethod
    async def add_machine(
        self,
        user_id: int,
        name: str,
        photo_file_id: Optional[str],
        muscle_ids: List[int],
    ) -> "Machine":
        """Добавляет новый тренажёр в личный список пользователя."""
        pass

    @abstractmethod
    async def get_user_machines(self, user_id: int) -> List["Machine"]:
        """Получает все тренажёры пользователя."""
        pass

    @abstractmethod
    async def get_machine_details(
        self, user_id: int, machine_id: int
    ) -> Optional["Machine"]:
        """Получает детали конкретного тренажёра пользователя."""
        pass

    @abstractmethod
    async def update_machine(
        self,
        user_id: int,
        machine_id: int,
        name: Optional[str],
        photo_file_id: Optional[str],
        muscle_ids: Optional[List[int]],
        is_archived: Optional[bool],
    ) -> Optional["Machine"]:
        """Обновляет существующий тренажёр."""
        pass

    @abstractmethod
    async def archive_machine(self, user_id: int, machine_id: int) -> bool:
        """Архивирует тренажёр, делая его неактивным для новых подходов."""
        pass


class IGoogleSheetsExportUseCase(ABC):
    @abstractmethod
    async def setup_google_sheets_config(self, user_id: int, sheet_url: str) -> bool:
        """Сохраняет URL и ID Google Sheet для пользователя."""
        pass

    @abstractmethod
    async def export_data_to_sheets(self, user_id: int) -> bool:
        """Экспортирует данные тренировок и тренажёров в Google Sheets."""
        pass


class ISystemUseCase(ABC):
    @abstractmethod
    async def get_registered_users(self) -> List["User"]:
        """Получает список всех зарегистрированных пользователей."""
        pass

    @abstractmethod
    async def check_user_registered(self, telegram_id: int) -> bool:
        """Проверяет, зарегистрирован ли пользователь."""
        pass
