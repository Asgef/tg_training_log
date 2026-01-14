import logging
from typing import Optional, List
from src.application.repositories import IMachineRepository, IMuscleRepository
from src.application.use_case_interfaces import IMachineManagementUseCase
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
                logger.warning(f"Пользователь {user_id} попытался добавить тренажёр с пустым названием.")
                raise ValueError("Название тренажера не может быть пустым.")

            existing_machine = await self.machine_repository.get_user_machine_by_name(
                user_id, name.strip()
            )
            if existing_machine:
                logger.warning(
                    f"Пользователь {user_id} попытался добавить дублирующееся название тренажёра: {name.strip()}"
                )
                raise ValueError(
                    f"Тренажер с названием '{name.strip()}' уже существует."
                )

            if muscle_ids:
                muscles = await self.muscle_repository.get_muscles_by_ids(muscle_ids)
                if len(muscles) != len(muscle_ids):
                    logger.warning(
                        f"Пользователь {user_id} предоставил неверные ID мышц: {muscle_ids}"
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
                f"Пользователь {user_id} добавил тренажёр {created_machine.id} ({created_machine.name})."
            )
            return created_machine
        except Exception as e:
            logger.error(f"Ошибка при добавлении тренажёра для пользователя {user_id}: {e}")
            raise

    async def get_user_machines(self, user_id: int) -> List[Machine]:
        try:
            machines = await self.machine_repository.get_user_machines(
                user_id, include_archived=False
            )
            logger.debug(f"Пользователь {user_id} получил {len(machines)} тренажёров.")
            return machines
        except Exception as e:
            logger.error(f"Ошибка при получении тренажёров для пользователя {user_id}: {e}")
            return []

    async def get_machine_details(
        self, user_id: int, machine_id: int
    ) -> Optional[Machine]:
        try:
            machine = await self.machine_repository.get_by_id(machine_id)
            if machine and machine.user_id == user_id:
                logger.debug(
                    f"Пользователь {user_id} получил детали тренажёра {machine_id}."
                )
                return machine
            logger.warning(
                f"Пользователь {user_id} попытался получить доступ к несуществующему или неавторизованному тренажёру {machine_id}."
            )
            return None
        except Exception as e:
            logger.error(
                f"Ошибка при получении деталей тренажёра {machine_id} для пользователя {user_id}: {e}"
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
                    f"Пользователь {user_id} попытался обновить несуществующий или неавторизованный тренажёр {machine_id}."
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
                            f"Пользователь {user_id} попытался переименовать тренажёр {machine_id} на дублирующееся название: {name.strip()}"
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
            logger.info(f"Пользователь {user_id} обновил тренажёр {machine_id}.")
            return updated_machine
        except Exception as e:
            logger.error(f"Ошибка при обновлении тренажёра {machine_id} для пользователя {user_id}: {e}")
            raise

    async def archive_machine(self, user_id: int, machine_id: int) -> bool:
        try:
            machine = await self.machine_repository.get_by_id(machine_id)
            if machine and machine.user_id == user_id and not machine.is_archived:
                machine.is_archived = True
                await self.machine_repository.update(machine)
                logger.info(f"Пользователь {user_id} архивировал тренажёр {machine_id}.")
                return True
            logger.warning(
                f"Пользователь {user_id} попытался архивировать несуществующий, неавторизованный или уже архивированный тренажёр {machine_id}."
            )
            return False
        except Exception as e:
            logger.error(
                f"Ошибка при архивации тренажёра {machine_id} для пользователя {user_id}: {e}"
            )
            return False
