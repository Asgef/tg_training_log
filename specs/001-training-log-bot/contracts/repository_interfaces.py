# ruff: noqa: F821
from abc import ABC, abstractmethod
from typing import List, Optional, Any
# Import domain models (assuming they will be defined in domain.py or similar)
# from domain import User, Machine, WorkoutSession, SetEntry, Muscle, MuscleZone

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
    async def get_by_telegram_id(self, telegram_id: int) -> Optional['User']: # Forward reference
        pass

    @abstractmethod
    async def get_admin_approved_users(self) -> List['User']:
        pass

    @abstractmethod
    async def save_google_sheet_config(self, user_id: int, url: str, spreadsheet_id: str) -> None:
        pass

class IMachineRepository(BaseRepository):
    @abstractmethod
    async def get_user_machines(self, user_id: int, include_archived: bool = False) -> List['Machine']:
        pass

    @abstractmethod
    async def get_user_machine_by_name(self, user_id: int, name: str) -> Optional['Machine']:
        pass

    @abstractmethod
    async def add_machine_with_tags(self, machine: 'Machine', zone_ids: List[int], muscle_ids: List[int]) -> 'Machine':
        pass

    @abstractmethod
    async def update_machine_muscles(self, machine_id: int, muscle_ids: List[int]) -> None:
        pass

    @abstractmethod
    async def update_machine_zones(self, machine_id: int, zone_ids: List[int]) -> None:
        pass

class IWorkoutSessionRepository(BaseRepository):
    @abstractmethod
    async def get_active_session_for_user(self, user_id: int) -> Optional['WorkoutSession']:
        pass

    @abstractmethod
    async def start_session(self, user_id: int) -> 'WorkoutSession':
        pass

    @abstractmethod
    async def end_session(self, session_id: int) -> None:
        pass

class ISetEntryRepository(BaseRepository):
    @abstractmethod
    async def add_set_entry(self, set_entry: 'SetEntry') -> 'SetEntry':
        pass

    @abstractmethod
    async def add_set_entry_snapshots(self, set_entry_id: int, zone_ids: List[int], muscle_ids: List[int]) -> None:
        pass

class IMuscleRepository(BaseRepository):
    @abstractmethod
    async def get_all_muscles(self) -> List['Muscle']:
        pass

    @abstractmethod
    async def get_muscles_by_ids(self, muscle_ids: List[int]) -> List['Muscle']:
        pass

class IMuscleZoneRepository(BaseRepository):
    @abstractmethod
    async def get_all_muscle_zones(self) -> List['MuscleZone']:
        pass