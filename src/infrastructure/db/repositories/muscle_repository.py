import logging
from typing import Optional, List, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from src.application.repositories import IMuscleRepository, IMuscleGroupRepository
from src.domain.models import Muscle, MuscleGroup

logger = logging.getLogger(__name__)


class MuscleRepository(IMuscleRepository, IMuscleGroupRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: Any) -> Optional[Muscle]:
        try:
            stmt = select(Muscle).where(Muscle.id == item_id)
            result = await self.session.execute(stmt)
            muscle = result.scalar_one_or_none()
            if muscle:
                logger.debug(f"Получена мышца {item_id}.")
            else:
                logger.debug(f"Мышца {item_id} не найдена.")
            return muscle
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_by_id для мышцы {item_id}: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_by_id для мышцы {item_id}: {e}",
                exc_info=True,
            )
            raise

    async def add(self, muscle: Muscle) -> Muscle:
        try:
            self.session.add(muscle)
            await self.session.commit()
            await self.session.refresh(muscle)
            logger.info(f"Добавлена новая мышца {muscle.id}.")
            return muscle
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при добавлении мышцы {muscle.id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при добавлении мышцы {muscle.id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise

    async def update(self, muscle: Muscle) -> Muscle:
        try:
            await self.session.commit()
            await self.session.refresh(muscle)
            logger.info(f"Обновлена мышца {muscle.id}.")
            return muscle
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при обновлении мышцы {muscle.id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при обновлении мышцы {muscle.id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise

    async def delete(self, item_id: Any) -> None:
        try:
            muscle = await self.get_by_id(item_id)
            if muscle:
                await self.session.delete(muscle)
                await self.session.commit()
                logger.info(f"Deleted muscle {item_id}.")
            else:
                logger.warning(f"Attempted to delete non-existent muscle {item_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при удалении мышцы {item_id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при удалении мышцы {item_id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise

    async def get_all_muscles(self) -> List[Muscle]:
        try:
            stmt = select(Muscle).options(selectinload(Muscle.group))
            result = await self.session.execute(stmt)
            muscles = list(result.scalars().all())
            logger.debug(f"Получено {len(muscles)} мышц.")
            return muscles
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError in get_all_muscles: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка в get_all_muscles: {e}", exc_info=True)
            raise

    async def get_muscles_by_ids(self, muscle_ids: List[int]) -> List[Muscle]:
        try:
            stmt = (
                select(Muscle)
                .where(Muscle.id.in_(muscle_ids))
                .options(selectinload(Muscle.group))
            )
            result = await self.session.execute(stmt)
            muscles = list(result.scalars().all())
            logger.debug(f"Получено {len(muscles)} мышц по ID: {muscle_ids}.")
            return muscles
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_muscles_by_ids {muscle_ids}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_muscles_by_ids {muscle_ids}: {e}",
                exc_info=True,
            )
            raise

    async def get_all_muscle_groups(self) -> List[MuscleGroup]:
        try:
            stmt = select(MuscleGroup)
            result = await self.session.execute(stmt)
            muscle_groups = list(result.scalars().all())
            logger.debug(f"Получено {len(muscle_groups)} групп мышц.")
            return muscle_groups
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_all_muscle_groups: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_all_muscle_groups: {e}", exc_info=True
            )
            raise

    async def get_muscle_group_by_id(self, item_id: Any) -> Optional[MuscleGroup]:
        try:
            stmt = select(MuscleGroup).where(MuscleGroup.id == item_id)
            result = await self.session.execute(stmt)
            muscle_group = result.scalar_one_or_none()
            if muscle_group:
                logger.debug(f"Retrieved muscle group {item_id}.")
            else:
                logger.debug(f"Muscle group {item_id} not found.")
            return muscle_group
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_muscle_group_by_id для группы {item_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_muscle_group_by_id for group {item_id}: {e}",
                exc_info=True,
            )
            raise

    async def add_muscle_group(self, muscle_group: MuscleGroup) -> MuscleGroup:
        try:
            self.session.add(muscle_group)
            await self.session.commit()
            await self.session.refresh(muscle_group)
            logger.info(
                f"Добавлена новая группа мышц {muscle_group.id} ({muscle_group.name})."
            )
            return muscle_group
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при добавлении группы мышц {muscle_group.name}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при добавлении группы мышц {muscle_group.name}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
