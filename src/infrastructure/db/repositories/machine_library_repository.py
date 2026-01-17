import logging
from typing import Optional, List, Any

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from src.application.repositories import IMachineLibraryRepository
from src.domain.models import MachineLibrary, MachineLibraryAlias

logger = logging.getLogger(__name__)


class MachineLibraryRepository(IMachineLibraryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: Any) -> Optional[MachineLibrary]:
        return await self.get_library_machine_by_id(int(item_id))

    async def add(self, item: MachineLibrary) -> MachineLibrary:
        try:
            self.session.add(item)
            await self.session.flush()
            await self.session.refresh(item)
            logger.info("Добавлен библиотечный тренажёр %s.", item.id)
            return item
        except SQLAlchemyError as e:
            logger.error(
                "SQLAlchemyError при добавлении библиотечного тренажёра: %s",
                e,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Неожиданная ошибка при добавлении библиотечного тренажёра: %s",
                e,
                exc_info=True,
            )
            raise

    async def update(self, item: MachineLibrary) -> MachineLibrary:
        try:
            await self.session.flush()
            await self.session.refresh(item)
            logger.info("Обновлён библиотечный тренажёр %s.", item.id)
            return item
        except SQLAlchemyError as e:
            logger.error(
                "SQLAlchemyError при обновлении библиотечного тренажёра %s: %s",
                item.id,
                e,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Неожиданная ошибка при обновлении библиотечного тренажёра %s: %s",
                item.id,
                e,
                exc_info=True,
            )
            raise

    async def delete(self, item_id: Any) -> None:
        try:
            item = await self.get_library_machine_by_id(int(item_id))
            if item:
                await self.session.delete(item)
                logger.info("Удалён библиотечный тренажёр %s.", item_id)
            else:
                logger.warning(
                    "Попытка удалить несуществующий библиотечный тренажёр %s.",
                    item_id,
                )
        except SQLAlchemyError as e:
            logger.error(
                "SQLAlchemyError при удалении библиотечного тренажёра %s: %s",
                item_id,
                e,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Неожиданная ошибка при удалении библиотечного тренажёра %s: %s",
                item_id,
                e,
                exc_info=True,
            )
            raise

    async def list_library_machines(
        self, limit: int = 20, offset: int = 0
    ) -> List[MachineLibrary]:
        try:
            stmt = (
                select(MachineLibrary)
                .options(selectinload(MachineLibrary.aliases))
                .order_by(MachineLibrary.name_ru.asc())
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                "SQLAlchemyError при получении списка библиотечных тренажёров: %s",
                e,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Неожиданная ошибка при получении списка библиотечных тренажёров: %s",
                e,
                exc_info=True,
            )
            raise

    async def search_library_machines(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> List[MachineLibrary]:
        try:
            normalized_query = query.strip()
            if not normalized_query:
                return await self.list_library_machines(limit=limit, offset=offset)

            like_query = f"%{normalized_query}%"
            stmt = (
                select(MachineLibrary)
                .outerjoin(
                    MachineLibraryAlias,
                    MachineLibraryAlias.machine_library_id == MachineLibrary.id,
                )
                .where(
                    or_(
                        MachineLibrary.name_ru.ilike(like_query),
                        MachineLibraryAlias.alias.ilike(like_query),
                    )
                )
                .options(selectinload(MachineLibrary.aliases))
                .order_by(MachineLibrary.name_ru.asc())
                .distinct()
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                "SQLAlchemyError при поиске библиотечных тренажёров '%s': %s",
                query,
                e,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Неожиданная ошибка при поиске библиотечных тренажёров '%s': %s",
                query,
                e,
                exc_info=True,
            )
            raise

    async def get_library_machine_by_id(
        self, machine_library_id: int
    ) -> Optional[MachineLibrary]:
        try:
            stmt = (
                select(MachineLibrary)
                .where(MachineLibrary.id == machine_library_id)
                .options(
                    selectinload(MachineLibrary.aliases),
                    selectinload(MachineLibrary.zones),
                    selectinload(MachineLibrary.muscles),
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(
                "SQLAlchemyError при получении библиотечного тренажёра %s: %s",
                machine_library_id,
                e,
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Неожиданная ошибка при получении библиотечного тренажёра %s: %s",
                machine_library_id,
                e,
                exc_info=True,
            )
            raise
