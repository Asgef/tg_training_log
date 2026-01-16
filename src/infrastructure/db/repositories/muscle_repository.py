import logging
from typing import Optional, List, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from src.application.repositories import IMuscleRepository, IMuscleZoneRepository
from src.domain.models import Muscle, MuscleZone, MuscleZoneMuscle

logger = logging.getLogger(__name__)


class MuscleRepository(IMuscleRepository, IMuscleZoneRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: Any) -> Optional[Muscle]:
        try:
            stmt = (
                select(Muscle)
                .where(Muscle.id == item_id)
                .options(selectinload(Muscle.zones))
                .execution_options(populate_existing=True)
            )
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
        """Добавляет мышцу в БД.
        
        Использует flush() для получения ID, но не делает commit().
        Управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            self.session.add(muscle)
            await self.session.flush()  # Получаем ID, но не коммитим транзакцию
            await self.session.refresh(muscle)
            logger.info(f"Добавлена новая мышца {muscle.id}.")
            return muscle
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при добавлении мышцы: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при добавлении мышцы: {e}", exc_info=True
            )
            raise

    async def update(self, muscle: Muscle) -> Muscle:
        """Обновляет мышцу в БД.
        
        Использует flush() для синхронизации изменений, но не делает commit().
        Управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            await self.session.flush()  # Синхронизируем изменения, но не коммитим
            await self.session.refresh(muscle)
            logger.info(f"Обновлена мышца {muscle.id}.")
            return muscle
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при обновлении мышцы {muscle.id}: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при обновлении мышцы {muscle.id}: {e}", exc_info=True
            )
            raise

    async def delete(self, item_id: Any) -> None:
        """Удаляет мышцу из БД.
        
        Не делает commit() - управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            muscle = await self.get_by_id(item_id)
            if muscle:
                await self.session.delete(muscle)
                # Не делаем commit() - это сделает middleware/use case
                logger.info(f"Deleted muscle {item_id}.")
            else:
                logger.warning(f"Attempted to delete non-existent muscle {item_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при удалении мышцы {item_id}: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при удалении мышцы {item_id}: {e}", exc_info=True
            )
            raise

    async def get_all_muscles(self) -> List[Muscle]:
        try:
            stmt = (
                select(Muscle)
                .options(selectinload(Muscle.zones))
                .execution_options(populate_existing=True)
            )
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
                .options(selectinload(Muscle.zones))
                .execution_options(populate_existing=True)
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

    async def get_muscles_by_zone_id(self, zone_id: int) -> List[Muscle]:
        try:
            stmt = (
                select(Muscle)
                .join(MuscleZoneMuscle, MuscleZoneMuscle.muscle_id == Muscle.id)
                .where(MuscleZoneMuscle.zone_id == zone_id)
                .options(selectinload(Muscle.zones))
            )
            result = await self.session.execute(stmt)
            muscles = list(result.scalars().all())
            logger.debug(f"Получено {len(muscles)} мышц для зоны {zone_id}.")
            return muscles
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_muscles_by_zone_id для зоны {zone_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_zone_muscle_links(self) -> List[dict]:
        """Возвращает связи зона↔мышца для REF_ZONE_MUSCLES."""
        try:
            stmt = (
                select(
                    MuscleZone.id.label("zone_id"),
                    MuscleZone.name.label("zone_name"),
                    Muscle.id.label("muscle_id"),
                    Muscle.name.label("muscle_name"),
                )
                .join(MuscleZoneMuscle, MuscleZoneMuscle.zone_id == MuscleZone.id)
                .join(Muscle, Muscle.id == MuscleZoneMuscle.muscle_id)
                .order_by(MuscleZone.id.asc(), Muscle.id.asc())
            )
            result = await self.session.execute(stmt)
            rows = result.mappings().all()
            return [dict(row) for row in rows]
        except SQLAlchemyError as e:
            logger.error(
                "SQLAlchemyError при получении связей зона↔мышца: %s",
                e,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Неожиданная ошибка при получении связей зона↔мышца: %s",
                e,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_muscles_by_zone_id для зоны {zone_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_all_muscle_zones(self) -> List[MuscleZone]:
        try:
            stmt = select(MuscleZone)
            result = await self.session.execute(stmt)
            muscle_zones = list(result.scalars().all())
            logger.debug(f"Получено {len(muscle_zones)} зон.")
            return muscle_zones
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_all_muscle_zones: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_all_muscle_zones: {e}", exc_info=True
            )
            raise

    async def get_muscle_zone_by_id(self, item_id: Any) -> Optional[MuscleZone]:
        try:
            stmt = select(MuscleZone).where(MuscleZone.id == item_id)
            result = await self.session.execute(stmt)
            muscle_zone = result.scalar_one_or_none()
            if muscle_zone:
                logger.debug(f"Получена зона {item_id}.")
            else:
                logger.debug(f"Зона {item_id} не найдена.")
            return muscle_zone
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_muscle_zone_by_id для зоны {item_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_muscle_zone_by_id for zone {item_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_muscle_zones_by_ids(self, zone_ids: List[int]) -> List[MuscleZone]:
        try:
            stmt = select(MuscleZone).where(MuscleZone.id.in_(zone_ids))
            result = await self.session.execute(stmt)
            zones = list(result.scalars().all())
            logger.debug(f"Получено {len(zones)} зон по ID: {zone_ids}.")
            return zones
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_muscle_zones_by_ids {zone_ids}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_muscle_zones_by_ids {zone_ids}: {e}",
                exc_info=True,
            )
            raise

    async def add_muscle_zone(self, muscle_zone: MuscleZone) -> MuscleZone:
        """Добавляет зону в БД.
        
        Использует flush() для получения ID, но не делает commit().
        Управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            self.session.add(muscle_zone)
            await self.session.flush()  # Получаем ID, но не коммитим транзакцию
            await self.session.refresh(muscle_zone)
            logger.info(
                f"Добавлена новая зона {muscle_zone.id} ({muscle_zone.name})."
            )
            return muscle_zone
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при добавлении зоны {muscle_zone.name}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при добавлении зоны {muscle_zone.name}: {e}",
                exc_info=True,
            )
            raise
