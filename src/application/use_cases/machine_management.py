import logging
from typing import Optional, List
from src.application.repositories import IMachineRepository, IMuscleRepository
from src.application.use_cases import IMachineManagementUseCase
from src.domain.models import Machine

logger = logging.getLogger(__name__)


class MachineManagementUseCase(IMachineManagementUseCase):
    def __init__(
        self,
        machine_repository: IMachineRepository,
        muscle_repository: IMuscleRepository,
    ):
        self.machine_repository = machine_repository
        self.muscle_repository = muscle_repository

    async def add_machine(
        self,
        user_id: int,
        name: str,
        photo_file_id: Optional[str],
        muscle_ids: List[int],
    ) -> Machine:
        try:
            if not name or len(name.strip()) == 0:
                logger.warning(f"User {user_id} tried to add machine with empty name.")
                raise ValueError("Название тренажера не может быть пустым.")

            existing_machine = await self.machine_repository.get_user_machine_by_name(
                user_id, name.strip()
            )
            if existing_machine:
                logger.warning(
                    f"User {user_id} tried to add duplicate machine name: {name.strip()}"
                )
                raise ValueError(
                    f"Тренажер с названием '{name.strip()}' уже существует."
                )

            if muscle_ids:
                muscles = await self.muscle_repository.get_muscles_by_ids(muscle_ids)
                if len(muscles) != len(muscle_ids):
                    logger.warning(
                        f"User {user_id} provided invalid muscle IDs: {muscle_ids}"
                    )
                    raise ValueError(
                        "Один или несколько указанных ID мышц не существуют."
                    )

            new_machine = Machine(
                user_id=user_id,
                name=name.strip(),
                photo_file_id=photo_file_id,
                is_archived=False,
            )
            created_machine = await self.machine_repository.add_machine_with_muscles(
                new_machine, muscle_ids
            )
            logger.info(
                f"User {user_id} added machine {created_machine.id} ({created_machine.name})."
            )
            return created_machine
        except Exception as e:
            logger.error(f"Error adding machine for user {user_id}: {e}")
            raise

    async def get_user_machines(self, user_id: int) -> List[Machine]:
        try:
            machines = await self.machine_repository.get_user_machines(
                user_id, include_archived=False
            )
            logger.debug(f"User {user_id} retrieved {len(machines)} machines.")
            return machines
        except Exception as e:
            logger.error(f"Error getting machines for user {user_id}: {e}")
            return []

    async def get_machine_details(
        self, user_id: int, machine_id: int
    ) -> Optional[Machine]:
        try:
            machine = await self.machine_repository.get_by_id(machine_id)
            if machine and machine.user_id == user_id:
                logger.debug(
                    f"User {user_id} retrieved details for machine {machine_id}."
                )
                return machine
            logger.warning(
                f"User {user_id} tried to access non-existent or unauthorized machine {machine_id}."
            )
            return None
        except Exception as e:
            logger.error(
                f"Error getting machine details for user {user_id}, machine {machine_id}: {e}"
            )
            return None

    async def update_machine(
        self,
        user_id: int,
        machine_id: int,
        name: Optional[str],
        photo_file_id: Optional[str],
        muscle_ids: Optional[List[int]],
        is_archived: Optional[bool],
    ) -> Optional[Machine]:
        try:
            machine = await self.machine_repository.get_by_id(machine_id)
            if not machine or machine.user_id != user_id:
                logger.warning(
                    f"User {user_id} tried to update non-existent or unauthorized machine {machine_id}."
                )
                return None

            if name:
                if name.strip() != machine.name:
                    existing_machine = (
                        await self.machine_repository.get_user_machine_by_name(
                            user_id, name.strip()
                        )
                    )
                    if existing_machine and existing_machine.id != machine_id:
                        logger.warning(
                            f"User {user_id} tried to rename machine {machine_id} to duplicate name: {name.strip()}"
                        )
                        raise ValueError(
                            f"Тренажер с названием '{name.strip()}' уже существует."
                        )
                machine.name = name.strip()
            if photo_file_id is not None:
                machine.photo_file_id = photo_file_id
            if is_archived is not None:
                machine.is_archived = is_archived

            updated_machine = await self.machine_repository.update(machine)
            logger.info(f"User {user_id} updated machine {machine_id}.")
            return updated_machine
        except Exception as e:
            logger.error(f"Error updating machine {machine_id} for user {user_id}: {e}")
            raise

    async def archive_machine(self, user_id: int, machine_id: int) -> bool:
        try:
            machine = await self.machine_repository.get_by_id(machine_id)
            if machine and machine.user_id == user_id and not machine.is_archived:
                machine.is_archived = True
                await self.machine_repository.update(machine)
                logger.info(f"User {user_id} archived machine {machine_id}.")
                return True
            logger.warning(
                f"User {user_id} tried to archive non-existent, unauthorized or already archived machine {machine_id}."
            )
            return False
        except Exception as e:
            logger.error(
                f"Error archiving machine {machine_id} for user {user_id}: {e}"
            )
            return False
