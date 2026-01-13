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
                logger.debug(f"Retrieved machine {item_id}.")
            else:
                logger.debug(f"Machine {item_id} not found.")
            return machine
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_by_id for machine {item_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_by_id for machine {item_id}: {e}",
                exc_info=True,
            )
            raise

    async def add(self, machine: Machine) -> Machine:
        try:
            self.session.add(machine)
            await self.session.commit()
            await self.session.refresh(machine)
            logger.info(f"Added new machine {machine.id} for user {machine.user_id}.")
            return machine
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in add machine for user {machine.user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in add machine for user {machine.user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def update(self, machine: Machine) -> Machine:
        try:
            await self.session.commit()
            await self.session.refresh(machine)
            logger.info(f"Updated machine {machine.id}.")
            return machine
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in update machine {machine.id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in update machine {machine.id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise

    async def delete(self, item_id: Any) -> None:
        try:
            machine = await self.get_by_id(item_id)
            if machine:
                await self.session.delete(machine)
                await self.session.commit()
                logger.info(f"Deleted machine {item_id}.")
            else:
                logger.warning(f"Attempted to delete non-existent machine {item_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in delete machine {item_id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in delete machine {item_id}: {e}", exc_info=True
            )
            await self.session.rollback()
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
            logger.debug(f"Retrieved {len(machines)} machines for user {user_id}.")
            return machines
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_user_machines for user {user_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_user_machines for user {user_id}: {e}",
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
                logger.debug(f"Retrieved machine by name '{name}' for user {user_id}.")
            else:
                logger.debug(f"Machine by name '{name}' for user {user_id} not found.")
            return machine
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_user_machine_by_name for user {user_id}, name '{name}': {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_user_machine_by_name for user {user_id}, name '{name}': {e}",
                exc_info=True,
            )
            raise

    async def add_machine_with_muscles(
        self, machine: Machine, muscle_ids: List[int]
    ) -> Machine:
        try:
            self.session.add(machine)
            await self.session.flush()

            for muscle_id in muscle_ids:
                machine_muscle = MachineMuscle(
                    machine_id=machine.id, muscle_id=muscle_id
                )
                self.session.add(machine_muscle)

            await self.session.commit()
            await self.session.refresh(machine)
            logger.info(
                f"Added new machine {machine.id} with muscles {muscle_ids} for user {machine.user_id}."
            )
            return machine
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in add_machine_with_muscles for user {machine.user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in add_machine_with_muscles for user {machine.user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
