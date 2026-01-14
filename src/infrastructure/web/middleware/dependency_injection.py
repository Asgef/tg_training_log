"""Dependency Injection middleware.

Инъектирует зависимости (use cases, repositories) в handlers через параметры.
"""
import structlog
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from src.container import Container

logger = structlog.get_logger(__name__)


class DependencyInjectionMiddleware(BaseMiddleware):
    """Middleware для инъекции зависимостей в handlers.
    
    Получает сессию БД из DatabaseMiddleware и создаёт все необходимые
    зависимости (repositories, use cases) для каждого запроса.
    """

    def __init__(self, container: Container):
        """Инициализация middleware.
        
        Args:
            container: DI контейнер приложения
        """
        self.container = container
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события с инъекцией зависимостей.
        
        Args:
            handler: Следующий handler в цепочке
            event: Telegram событие
            data: Данные для передачи в handler
            
        Returns:
            Результат выполнения handler
        """
        # Получаем сессию из data (инъектируется DatabaseMiddleware)
        session: AsyncSession = data.get("db_session")
        if session is None:
            logger.error("Database session not found in middleware data")
            raise ValueError("Database session not found in middleware data")
        
        # Создаём репозитории с текущей сессией
        user_repo = self.container.user_repository(session=session)
        machine_repo = self.container.machine_repository(session=session)
        muscle_repo = self.container.muscle_repository(session=session)
        workout_session_repo = self.container.workout_session_repository(session=session)
        set_entry_repo = self.container.set_entry_repository(session=session)
        processed_update_repo = self.container.processed_update_repository(session=session)
        
        # Создаём Google Sheets client (singleton, не зависит от сессии)
        try:
            google_sheets_client = self.container.google_sheets_client()
        except Exception as e:
            logger.warning("Failed to initialize Google Sheets client", error=str(e))
            google_sheets_client = None
        
        # Инъецируем use cases в data
        data["registration_use_case"] = self.container.registration_use_case(
            user_repository=user_repo
        )
        data["workout_use_case"] = self.container.workout_use_case(
            workout_session_repository=workout_session_repo,
            set_entry_repository=set_entry_repo,
            machine_repository=machine_repo,
        )
        data["machine_management_use_case"] = self.container.machine_management_use_case(
            machine_repository=machine_repo,
            muscle_repository=muscle_repo,
        )
        data["google_sheets_export_use_case"] = self.container.google_sheets_export_use_case(
            user_repository=user_repo,
            machine_repository=machine_repo,
            set_entry_repository=set_entry_repo,
            google_sheets_client=google_sheets_client,
        )
        
        # Инъецируем репозитории напрямую (для middleware)
        data["muscle_repository"] = muscle_repo
        data["user_repository"] = user_repo
        data["processed_update_repository"] = processed_update_repo
        
        return await handler(event, data)
