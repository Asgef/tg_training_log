import logging
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.application.repositories import ISetEntryRepository
from src.domain.models import SetEntry

logger = logging.getLogger(__name__)


class SetEntryRepository(ISetEntryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: Any) -> Optional[SetEntry]:
        try:
            stmt = select(SetEntry).where(SetEntry.id == item_id)
            result = await self.session.execute(stmt)
            set_entry = result.scalar_one_or_none()
            if set_entry:
                logger.debug(f"Получен подход {item_id}.")
            else:
                logger.debug(f"Подход {item_id} не найден.")
            return set_entry
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_by_id for set entry {item_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_by_id для подхода {item_id}: {e}",
                exc_info=True,
            )
            raise

    async def add(self, set_entry: SetEntry) -> SetEntry:
        """Добавляет подход в БД.
        
        Использует flush() для получения ID, но не делает commit().
        Управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            self.session.add(set_entry)
            await self.session.flush()  # Получаем ID, но не коммитим транзакцию
            await self.session.refresh(set_entry)
            logger.info(
                f"Добавлен новый подход {set_entry.id} для сессии {set_entry.session_id}."
            )
            return set_entry
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при добавлении подхода для сессии {set_entry.session_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при добавлении подхода для сессии {set_entry.session_id}: {e}",
                exc_info=True,
            )
            raise

    async def update(self, set_entry: SetEntry) -> SetEntry:
        """Обновляет подход в БД.
        
        Использует flush() для синхронизации изменений, но не делает commit().
        Управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            await self.session.flush()  # Синхронизируем изменения, но не коммитим
            await self.session.refresh(set_entry)
            logger.info(f"Обновлён подход {set_entry.id}.")
            return set_entry
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in update set entry {set_entry.id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при обновлении подхода {set_entry.id}: {e}",
                exc_info=True,
            )
            raise

    async def delete(self, item_id: Any) -> None:
        """Удаляет подход из БД.
        
        Не делает commit() - управление транзакцией осуществляется на уровне middleware/use case.
        """
        try:
            set_entry = await self.get_by_id(item_id)
            if set_entry:
                await self.session.delete(set_entry)
                # Не делаем commit() - это сделает middleware/use case
                logger.info(f"Deleted set entry {item_id}.")
            else:
                logger.warning(f"Attempted to delete non-existent set entry {item_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при удалении подхода {item_id}: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при удалении подхода {item_id}: {e}", exc_info=True
            )
            raise

    async def add_set_entry(self, set_entry: SetEntry) -> SetEntry:
        # Этот метод избыточен с add(), но требуется интерфейсом
        return await self.add(set_entry)
