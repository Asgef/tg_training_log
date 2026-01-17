import logging
from typing import List

from src.application.repositories import IMachineLibraryRepository, IMachineRepository
from src.application.use_case_interfaces import IMachineLibraryUseCase
from src.application.dto import (
    MachineDTO,
    MachineLibraryDTO,
    MachineLibraryItemDTO,
    machine_library_to_dto,
    machine_library_to_item_dto,
    machine_to_dto,
)
from src.domain.models import Machine

logger = logging.getLogger(__name__)


class MachineLibraryUseCase(IMachineLibraryUseCase):
    def __init__(
        self,
        machine_library_repository: IMachineLibraryRepository,
        machine_repository: IMachineRepository,
    ):
        self.machine_library_repository = machine_library_repository
        self.machine_repository = machine_repository

    async def list_library_machines(
        self, limit: int = 20, offset: int = 0
    ) -> List[MachineLibraryItemDTO]:
        machines = await self.machine_library_repository.list_library_machines(
            limit=limit, offset=offset
        )
        return [machine_library_to_item_dto(item) for item in machines]

    async def search_library_machines(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> List[MachineLibraryItemDTO]:
        machines = await self.machine_library_repository.search_library_machines(
            query=query, limit=limit, offset=offset
        )
        return [machine_library_to_item_dto(item) for item in machines]

    async def get_library_machine_details(
        self, machine_library_id: int
    ) -> MachineLibraryDTO | None:
        machine = await self.machine_library_repository.get_library_machine_by_id(
            machine_library_id
        )
        if not machine:
            return None
        return machine_library_to_dto(machine)

    async def add_machine_from_library(
        self, user_id: int, machine_library_id: int
    ) -> MachineDTO:
        library_machine = await self.machine_library_repository.get_library_machine_by_id(
            machine_library_id
        )
        if not library_machine:
            logger.warning(
                "Попытка создать тренажёр из несуществующей записи библиотеки %s.",
                machine_library_id,
            )
            raise ValueError("Библиотечный тренажёр не найден.")

        zone_ids = [zone.id for zone in library_machine.zones] if library_machine.zones else []
        muscle_ids = [muscle.id for muscle in library_machine.muscles] if library_machine.muscles else []

        unique_name = await self._generate_unique_machine_name(
            user_id, library_machine.name_ru
        )
        new_machine = Machine(
            user_id=user_id,
            name=unique_name,
            photo_file_id=None,
            is_archived=False,
            library_machine_id=library_machine.id,
        )
        created_machine = await self.machine_repository.add_machine_with_tags(
            new_machine, zone_ids, muscle_ids
        )
        logger.info(
            "Пользователь %s добавил тренажёр из библиотеки %s как %s.",
            user_id,
            machine_library_id,
            created_machine.id,
        )
        return machine_to_dto(created_machine)

    async def _generate_unique_machine_name(self, user_id: int, base_name: str) -> str:
        candidate = base_name.strip()
        suffix = 1
        while True:
            existing = await self.machine_repository.get_user_machine_by_name(
                user_id, candidate
            )
            if not existing or existing.is_archived:
                return candidate
            suffix += 1
            candidate = f"{base_name.strip()} ({suffix})"
