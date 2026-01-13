from abc import ABC, abstractmethod
from typing import Optional, List

# Import domain models
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
        """Handles user's registration request."""
        pass

    @abstractmethod
    async def approve_registration(self, user_id: int) -> bool:
        """Approves a user's registration."""
        pass

    @abstractmethod
    async def reject_registration(self, user_id: int) -> bool:
        """Rejects a user's registration."""
        pass


class IWorkoutUseCase(ABC):
    @abstractmethod
    async def start_new_workout(self, user_id: int) -> Optional["WorkoutSession"]:
        """Starts a new workout session for the user."""
        pass

    @abstractmethod
    async def end_current_workout(self, user_id: int) -> Optional["WorkoutSession"]:
        """Ends the user's current active workout session."""
        pass

    @abstractmethod
    async def record_set(
        self, user_id: int, machine_id: int, weight: float, reps: int, failure: bool
    ) -> Optional["SetEntry"]:
        """Records a set for the active workout session."""
        pass

    @abstractmethod
    async def get_active_workout_session(
        self, user_id: int
    ) -> Optional["WorkoutSession"]:
        """Retrieves the active workout session for a user."""
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
        """Adds a new machine to the user's personal list."""
        pass

    @abstractmethod
    async def get_user_machines(self, user_id: int) -> List["Machine"]:
        """Retrieves all machines for a user."""
        pass

    @abstractmethod
    async def get_machine_details(
        self, user_id: int, machine_id: int
    ) -> Optional["Machine"]:
        """Retrieves details of a specific machine for a user."""
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
        """Updates an existing machine."""
        pass

    @abstractmethod
    async def archive_machine(self, user_id: int, machine_id: int) -> bool:
        """Archives a machine, making it inactive for new sets."""
        pass


class IGoogleSheetsExportUseCase(ABC):
    @abstractmethod
    async def setup_google_sheets_config(self, user_id: int, sheet_url: str) -> bool:
        """Saves Google Sheet URL and ID for a user."""
        pass

    @abstractmethod
    async def export_data_to_sheets(self, user_id: int) -> bool:
        """Exports workout and machine data to Google Sheets."""
        pass


class ISystemUseCase(ABC):
    @abstractmethod
    async def get_registered_users(self) -> List["User"]:
        """Retrieves a list of all registered users."""
        pass

    @abstractmethod
    async def check_user_registered(self, telegram_id: int) -> bool:
        """Checks if a user is registered."""
        pass
