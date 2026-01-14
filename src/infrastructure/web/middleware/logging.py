"""Middleware для структурированного логирования.

Добавляет correlation_id и контекст (user_id, chat_id, update_id) в логи.
"""
import uuid
from typing import Callable, Dict, Any, Awaitable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для добавления контекста логирования.
    
    Генерирует correlation_id для каждого запроса и добавляет контекст:
    - user_id
    - chat_id
    - update_id
    - correlation_id
    
    Должен быть зарегистрирован ПЕРВЫМ, чтобы контекст был доступен во всех последующих middleware и handlers.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события с добавлением контекста логирования.
        
        Args:
            handler: Следующий handler в цепочке
            event: Telegram событие
            data: Данные для передачи в handler
            
        Returns:
            Результат выполнения handler
        """
        # Генерируем correlation_id для этого запроса
        correlation_id = str(uuid.uuid4())
        
        # Получаем Update объект
        update: Update | None = data.get("event_update")
        
        # Извлекаем контекст из события
        user_id: int | None = None
        chat_id: int | None = None
        update_id: int | None = None
        
        if update:
            update_id = update.update_id
            
            # Извлекаем user_id и chat_id из разных типов событий
            if isinstance(event, Message):
                if event.from_user:
                    user_id = event.from_user.id
                if event.chat:
                    chat_id = event.chat.id
            elif isinstance(event, CallbackQuery):
                if event.from_user:
                    user_id = event.from_user.id
                if event.message and event.message.chat:
                    chat_id = event.message.chat.id
                elif event.message is None and hasattr(event, "chat") and event.chat:
                    chat_id = event.chat.id  # type: ignore
            
            # Пробуем получить из других полей update
            if user_id is None:
                if update.message and update.message.from_user:
                    user_id = update.message.from_user.id
                elif update.callback_query and update.callback_query.from_user:
                    user_id = update.callback_query.from_user.id
                elif update.edited_message and update.edited_message.from_user:
                    user_id = update.edited_message.from_user.id
            
            if chat_id is None:
                if update.message and update.message.chat:
                    chat_id = update.message.chat.id
                elif update.callback_query and update.callback_query.message and update.callback_query.message.chat:
                    chat_id = update.callback_query.message.chat.id
                elif update.edited_message and update.edited_message.chat:
                    chat_id = update.edited_message.chat.id
        
        # Добавляем контекст в structlog contextvars
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            update_id=update_id,
            user_id=user_id,
            chat_id=chat_id,
        )
        
        # Добавляем в data для использования в handlers
        data["correlation_id"] = correlation_id
        data["log_user_id"] = user_id
        data["log_chat_id"] = chat_id
        data["log_update_id"] = update_id
        
        try:
            # Выполняем handler с контекстом
            result = await handler(event, data)
            return result
        finally:
            # Очищаем контекст после обработки
            structlog.contextvars.clear_contextvars()
