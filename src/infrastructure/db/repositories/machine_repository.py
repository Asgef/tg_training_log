import logging
from typing import Optional, List, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from src.application.repositories import IMachineRepository
from src.domain.models import Machine, MachineMuscle

logger = logging.getLogger(__name__)


class MachineRepository(IMachineRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: Any) -> Optional[Machine]:
        try:
            stmt = (
                select(Machine)
                .where(Machine.id == item_id)
                .options(selectinload(Machine.muscles))
            )
            result = await self.session.execute(stmt)
            machine = result.scalar_one_or_none()
            if machine:
                logger.debug(f"Получен тренажёр {item_id}.")
            else:
                logger.debug(f"Тренажёр {item_id} не найден.")
            return machine
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_by_id для тренажёра {item_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_by_id для тренажёра {item_id}: {e}",
                exc_info=True,
            )
            raise

    async def add(self, machine: Machine) -> Machine:
        """Добавляет тренажёр в БД.
        
        Использует flush() для получения ID, но не делает commit().
        Управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            self.session.add(machine)
            await self.session.flush()  # Получаем ID, но не коммитим транзакцию
            await self.session.refresh(machine)
            logger.info(f"Добавлен новый тренажёр {machine.id} для пользователя {machine.user_id}.")
            return machine
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при добавлении тренажёра для пользователя {machine.user_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при добавлении тренажёра для пользователя {machine.user_id}: {e}",
                exc_info=True,
            )
            raise

    async def update(self, machine: Machine) -> Machine:
        """Обновляет тренажёр в БД.
        
        Использует flush() для синхронизации изменений, но не делает commit().
        Управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            await self.session.flush()  # Синхронизируем изменения, но не коммитим
            await self.session.refresh(machine)
            logger.info(f"Обновлён тренажёр {machine.id}.")
            return machine
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при обновлении тренажёра {machine.id}: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при обновлении тренажёра {machine.id}: {e}", exc_info=True
            )
            raise

    async def delete(self, item_id: Any) -> None:
        """Удаляет тренажёр из БД.
        
        Не делает commit() - управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            machine = await self.get_by_id(item_id)
            if machine:
                await self.session.delete(machine)
                # Не делаем commit() - это сделает middleware/use case
                logger.info(f"Удалён тренажёр {item_id}.")
            else:
                logger.warning(f"Попытка удалить несуществующий тренажёр {item_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при удалении тренажёра {item_id}: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при удалении тренажёра {item_id}: {e}", exc_info=True
            )
            raise

    async def get_user_machines(
        self, user_id: int, include_archived: bool = False
    ) -> List[Machine]:
        try:
            stmt = select(Machine).where(Machine.user_id == user_id)
            if not include_archived:
                stmt = stmt.where(Machine.is_archived.is_(False))
            stmt = stmt.options(selectinload(Machine.muscles))
            result = await self.session.execute(stmt)
            machines = list(result.scalars().all())
            logger.debug(f"Получено {len(machines)} тренажёров для пользователя {user_id}.")
            return machines
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_user_machines для пользователя {user_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_user_machines для пользователя {user_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_user_machine_by_name(
        self, user_id: int, name: str
    ) -> Optional[Machine]:
        try:
            stmt = (
                select(Machine)
                .where(Machine.user_id == user_id, Machine.name == name)
                .options(selectinload(Machine.muscles))
            )
            result = await self.session.execute(stmt)
            machine = result.scalar_one_or_none()
            if machine:
                logger.debug(f"Получен тренажёр по имени '{name}' для пользователя {user_id}.")
            else:
                logger.debug(f"Тренажёр по имени '{name}' для пользователя {user_id} не найден.")
            return machine
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_user_machine_by_name для пользователя {user_id}, имя '{name}': {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_user_machine_by_name для пользователя {user_id}, имя '{name}': {e}",
                exc_info=True,
            )
            raise

    async def add_machine_with_muscles(
        self, machine: Machine, muscle_ids: List[int]
    ) -> Machine:
        """Добавляет тренажёр с мышцами в БД.
        
        Использует flush() для получения ID, но не делает commit().
        Управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            self.session.add(machine)
            await self.session.flush()  # Получаем ID тренажёра

            for muscle_id in muscle_ids:
                machine_muscle = MachineMuscle(
                    machine_id=machine.id, muscle_id=muscle_id
                )
                self.session.add(machine_muscle)

            await self.session.flush()  # Синхронизируем связи, но не коммитим
            await self.session.refresh(machine)
            logger.info(
                f"Добавлен новый тренажёр {machine.id} с мышцами {muscle_ids} для пользователя {machine.user_id}."
            )
            return machine
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при добавлении тренажёра с мышцами для пользователя {machine.user_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при добавлении тренажёра с мышцами для пользователя {machine.user_id}: {e}",
                exc_info=True,
            )
            raise

    async def update_machine_muscles(
        self, machine_id: int, muscle_ids: List[int]
    ) -> None:
        """Обновляет связи тренажёра с мышцами.
        
        Не делает commit() - управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            # Удаляем все существующие связи
            stmt = select(MachineMuscle).where(MachineMuscle.machine_id == machine_id)
            result = await self.session.execute(stmt)
            existing_links = result.scalars().all()
            
            for link in existing_links:
                await self.session.delete(link)
            
            # Добавляем новые связи
            for muscle_id in muscle_ids:
                machine_muscle = MachineMuscle(
                    machine_id=machine_id, muscle_id=muscle_id
                )
                self.session.add(machine_muscle)
            
            # Не делаем commit() - это сделает middleware/use case
            logger.info(
                f"Обновлены мышцы для тренажёра {machine_id}: {muscle_ids}."
            )
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при обновлении мышц тренажёра {machine_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при обновлении мышц тренажёра {machine_id}: {e}",
                exc_info=True,
            )
            raise
