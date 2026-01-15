from abc import ABC, abstractmethod
from typing import Optional, List

# Импорт DTO
from src.application.dto import (
    UserDTO,
    MachineDTO,
    WorkoutSessionDTO,
    SetEntryDTO,
    MuscleDTO,
    MuscleGroupDTO,
)


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

    @abstractmethod
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[UserDTO]:
        """Получает пользователя по Telegram ID."""
        pass

    @abstractmethod
    async def check_user_registered(self, telegram_id: int) -> bool:
        """Проверяет, зарегистрирован ли пользователь."""
        pass


class IWorkoutUseCase(ABC):
    @abstractmethod
    async def start_new_workout(self, user_id: int) -> Optional[WorkoutSessionDTO]:
        """Начинает новую тренировку для пользователя."""
        pass

    @abstractmethod
    async def end_current_workout(self, user_id: int) -> Optional[WorkoutSessionDTO]:
        """Завершает текущую активную тренировку пользователя."""
        pass

    @abstractmethod
    async def record_set(
        self, user_id: int, machine_id: int, weight: float, reps: int, failure: bool
    ) -> Optional[SetEntryDTO]:
        """Записывает подход для активной тренировки."""
        pass

    @abstractmethod
    async def get_active_workout_session(
        self, user_id: int
    ) -> Optional[WorkoutSessionDTO]:
        """Получает активную тренировку пользователя."""
        pass

    @abstractmethod
    async def get_recent_machine_ids(self, user_id: int, limit: int = 5) -> List[int]:
        """Получает последние использованные тренажёры пользователя."""
        pass

    @abstractmethod
    async def get_last_set_for_machine(
        self, user_id: int, machine_id: int
    ) -> Optional[SetEntryDTO]:
        """Получает последний подход пользователя по тренажёру."""
        pass


class IMachineManagementUseCase(ABC):
    @abstractmethod
    async def add_machine(
        self,
        user_id: int,
        name: str,
        photo_file_id: Optional[str],
        muscle_ids: List[int],
    ) -> MachineDTO:
        """Добавляет новый тренажёр в личный список пользователя."""
        pass

    @abstractmethod
    async def get_user_machines(self, user_id: int) -> List[MachineDTO]:
        """Получает все тренажёры пользователя."""
        pass

    @abstractmethod
    async def get_machine_details(
        self, user_id: int, machine_id: int
    ) -> Optional[MachineDTO]:
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
    ) -> Optional[MachineDTO]:
        """Обновляет существующий тренажёр."""
        pass

    @abstractmethod
    async def archive_machine(self, user_id: int, machine_id: int) -> bool:
        """Архивирует тренажёр, делая его неактивным для новых подходов."""
        pass

    @abstractmethod
    async def check_machine_name_exists(self, user_id: int, name: str) -> bool:
        """Проверяет, существует ли тренажёр с таким именем у пользователя."""
        pass

    @abstractmethod
    async def get_all_muscle_groups(self) -> List[MuscleGroupDTO]:
        """Получает все группы мышц."""
        pass

    @abstractmethod
    async def get_muscles_by_group_id(self, group_id: int) -> List[MuscleDTO]:
        """Получает мышцы по ID группы."""
        pass

    @abstractmethod
    async def get_muscle_group_by_id(self, group_id: int) -> Optional[MuscleGroupDTO]:
        """Получает группу мышц по ID."""
        pass

    @abstractmethod
    async def get_all_muscles(self) -> List[MuscleDTO]:
        """Получает все мышцы."""
        pass

    @abstractmethod
    async def get_muscles_by_ids(self, muscle_ids: List[int]) -> List[MuscleDTO]:
        """Получает мышцы по списку ID."""
        pass

    @abstractmethod
    async def get_muscle_by_id(self, muscle_id: int) -> Optional[MuscleDTO]:
        """Получает мышцу по ID."""
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
    async def get_registered_users(self) -> List[UserDTO]:
        """Получает список всех зарегистрированных пользователей."""
        pass

    @abstractmethod
    async def check_user_registered(self, telegram_id: int) -> bool:
        """Проверяет, зарегистрирован ли пользователь."""
        pass
