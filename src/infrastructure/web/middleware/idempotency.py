"""Middleware для обеспечения идемпотентности обработки Telegram updates.

Проверяет, был ли update уже обработан, и пропускает повторные запросы.
"""
import structlog
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.repositories import IProcessedUpdateRepository

logger = structlog.get_logger(__name__)


class IdempotencyMiddleware(BaseMiddleware):
    """Middleware для обеспечения идемпотентности обработки Telegram updates.
    
    Проверяет update_id и пропускает уже обработанные updates.
    Должен быть зарегистрирован ПОСЛЕ DatabaseMiddleware, чтобы иметь доступ к сессии БД.
    """
    
    def __init__(self):
        """Инициализация middleware."""
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события с проверкой идемпотентности.
        
        Args:
            handler: Следующий handler в цепочке
            event: Telegram событие
            data: Данные для передачи в handler
            
        Returns:
            Результат выполнения handler или None если update уже обработан
        """
        # Получаем Update объект из data
        update: Update | None = data.get("event_update")
        
        if update is None:
            # Если нет Update объекта, пропускаем проверку и продолжаем обработку
            logger.warning("Update object not found in data, skipping idempotency check")
            return await handler(event, data)
        
        update_id = update.update_id
        
        # Получаем сессию БД из data (инъектируется DatabaseMiddleware)
        session: AsyncSession | None = data.get("db_session")
        if session is None:
            logger.error("Database session not found in middleware data, skipping idempotency check")
            return await handler(event, data)
        
        # Получаем репозиторий из контейнера (инъектируется DependencyInjectionMiddleware)
        processed_update_repository: IProcessedUpdateRepository | None = data.get("processed_update_repository")
        if processed_update_repository is None:
            logger.error("ProcessedUpdateRepository not found in middleware data, skipping idempotency check")
            return await handler(event, data)
        
        # Используем savepoint для изоляции проверки идемпотентности
        # Это позволяет при ошибке откатить только эту часть, не ломая всю транзакцию
        savepoint = None
        try:
            # Создаём savepoint для проверки идемпотентности
            savepoint = await session.begin_nested()
            
            # Проверяем, был ли update уже обработан
            is_processed = await processed_update_repository.is_processed(update_id)
            
            if is_processed:
                logger.info("Update already processed, skipping", update_id=update_id)
                # Коммитим savepoint перед возвратом
                await savepoint.commit()
                # Для CallbackQuery нужно ответить, чтобы не показывать loading
                from aiogram.types import CallbackQuery
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer()  # type: ignore
                    except Exception:
                        pass  # Игнорируем ошибки при ответе на уже обработанный callback
                return None  # Пропускаем обработку
            
            # Помечаем update как обработанный ПЕРЕД обработкой
            # Это предотвращает race conditions при параллельной обработке
            await processed_update_repository.mark_as_processed(update_id)
            
            # Коммитим savepoint - проверка идемпотентности прошла успешно
            await savepoint.commit()
            
            # Продолжаем обработку
            result = await handler(event, data)
            
            return result
            
        except Exception as e:
            logger.error(
                "Error in idempotency middleware",
                update_id=update_id,
                error=str(e),
                exc_info=True,
            )
            # В случае ошибки откатываем savepoint, чтобы не ломать основную транзакцию
            if savepoint is not None:
                try:
                    await savepoint.rollback()
                    logger.debug("Rolled back savepoint after idempotency error", update_id=update_id)
                except Exception as rollback_error:
                    logger.error(
                        "Error during savepoint rollback in idempotency middleware",
                        update_id=update_id,
                        error=str(rollback_error),
                        exc_info=True,
                    )
            # Продолжаем обработку без проверки идемпотентности
            # Это лучше, чем полностью блокировать бота
            logger.warning("Skipping idempotency check due to error, continuing with handler", update_id=update_id)
            return await handler(event, data)
