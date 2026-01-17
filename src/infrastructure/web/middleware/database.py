"""Database middleware для управления сессиями БД.

Создаёт новую сессию для каждого запроса и автоматически
делает commit при успехе или rollback при ошибке.
"""
import structlog
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для управления сессиями БД.
    
    Создаёт новую сессию для каждого запроса через session_factory
    и автоматически делает commit при успехе или rollback при ошибке.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Инициализация middleware.
        
        Args:
            session_factory: async_sessionmaker для создания сессий
        """
        self.session_factory = session_factory
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события с созданием сессии БД.
        
        Args:
            handler: Следующий handler в цепочке
            event: Telegram событие
            data: Данные для передачи в handler
            
        Returns:
            Результат выполнения handler
        """
        async with self.session_factory() as session:
            # Инъектируем сессию в data
            data["db_session"] = session
            data["db_session_factory"] = self.session_factory
            
            try:
                result = await handler(event, data)
                # Делаем commit при успешном выполнении handler
                await session.commit()
                return result
            except Exception as e:
                # Делаем rollback при ошибке
                await session.rollback()
                logger.error("Error in handler, session rolled back", error=str(e), exc_info=True)
                raise
            # Сессия автоматически закроется при выходе из context manager
