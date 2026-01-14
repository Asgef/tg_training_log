"""Репозиторий для работы с обработанными Telegram updates."""
import logging
from typing import Any
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.application.repositories import IProcessedUpdateRepository
from src.domain.models import ProcessedUpdate

logger = logging.getLogger(__name__)


class ProcessedUpdateRepository(IProcessedUpdateRepository):
    """Реализация репозитория для работы с обработанными Telegram updates."""
    
    def __init__(self, session: AsyncSession):
        """Инициализация репозитория.
        
        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        self.session = session
    
    async def is_processed(self, update_id: int) -> bool:
        """Проверяет, был ли update уже обработан.
        
        Args:
            update_id: ID Telegram update
            
        Returns:
            True если update уже обработан, False иначе
        """
        try:
            stmt = select(ProcessedUpdate).where(ProcessedUpdate.update_id == update_id)
            result = await self.session.execute(stmt)
            processed = result.scalar_one_or_none()
            return processed is not None
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в is_processed для update_id {update_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в is_processed для update_id {update_id}: {e}",
                exc_info=True,
            )
            raise
    
    async def mark_as_processed(self, update_id: int) -> None:
        """Помечает update как обработанный.
        
        Args:
            update_id: ID Telegram update
        """
        try:
            processed_update = ProcessedUpdate(
                update_id=update_id,
                processed_at=datetime.now(timezone.utc)
            )
            self.session.add(processed_update)
            # Не делаем commit() - это сделает middleware/use case
            logger.debug(f"Marked update {update_id} as processed.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в mark_as_processed для update_id {update_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в mark_as_processed для update_id {update_id}: {e}",
                exc_info=True,
            )
            raise
    
    async def cleanup_old_updates(self, hours: int = 24) -> int:
        """Удаляет старые записи о processed updates.
        
        Args:
            hours: Количество часов, после которых записи считаются старыми (по умолчанию 24)
            
        Returns:
            Количество удалённых записей
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            stmt = delete(ProcessedUpdate).where(
                ProcessedUpdate.processed_at < cutoff_time
            )
            result = await self.session.execute(stmt)
            deleted_count = result.rowcount
            # Не делаем commit() - это сделает middleware/use case
            logger.info(f"Cleaned up {deleted_count} old processed updates (older than {hours} hours).")
            return deleted_count
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в cleanup_old_updates: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в cleanup_old_updates: {e}",
                exc_info=True,
            )
            raise
