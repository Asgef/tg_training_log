"""Middleware для глобальной обработки ошибок."""
from typing import Callable, Dict, Any, Awaitable
import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from pydantic import ValidationError as PydanticValidationError

from src.infrastructure.web.handlers.errors import (
    BaseApplicationError,
    ErrorMessages,
)

logger = structlog.get_logger(__name__)


class ErrorHandlingMiddleware(BaseMiddleware):
    """Middleware для глобальной обработки ошибок в handlers.
    
    Перехватывает все исключения, возникающие в handlers, логирует их
    и отправляет понятные сообщения пользователям.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события с перехватом ошибок.
        
        Args:
            handler: Следующий handler в цепочке
            event: Telegram событие
            data: Данные для передачи в handler
            
        Returns:
            Результат выполнения handler или None при ошибке
        """
        # Получаем user_id из события
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id if event.from_user else None
        
        try:
            return await handler(event, data)
        
        except BaseApplicationError as e:
            # Обработка кастомных ошибок приложения
            await self._handle_application_error(e, event, user_id)
            return None
        
        except PydanticValidationError as e:
            # Обработка ошибок валидации Pydantic
            await self._handle_validation_error(e, event, user_id)
            return None
        
        except ValueError as e:
            # Обработка ValueError (обычно ошибки валидации)
            await self._handle_value_error(e, event, user_id)
            return None
        
        except TelegramBadRequest as e:
            # Обработка ошибок Telegram API (например, "message is not modified")
            await self._handle_telegram_error(e, event, user_id)
            # Не возвращаем None, чтобы не блокировать обработку
            # Некоторые ошибки Telegram (например, "message is not modified") не критичны
            if "message is not modified" in str(e).lower():
                return None
            raise  # Пробрасываем дальше для других ошибок Telegram
        
        except TelegramAPIError as e:
            # Обработка других ошибок Telegram API
            await self._handle_telegram_api_error(e, event, user_id)
            return None
        
        except Exception as e:
            # Обработка всех остальных неожиданных ошибок
            await self._handle_unexpected_error(e, event, user_id)
            return None
    
    async def _handle_application_error(
        self,
        error: BaseApplicationError,
        event: TelegramObject,
        user_id: int | None,
    ) -> None:
        """Обработать кастомную ошибку приложения.
        
        Args:
            error: Ошибка приложения
            event: Telegram событие
            user_id: ID пользователя
        """
        logger.warning(
            "Ошибка приложения",
            event_type="application_error",
            user_id=user_id,
            error_code=error.error_code,
            error_message=error.message,
            exc_info=True,
        )
        
        await self._send_error_message(event, error.user_message)
    
    async def _handle_validation_error(
        self,
        error: PydanticValidationError,
        event: TelegramObject,
        user_id: int | None,
    ) -> None:
        """Обработать ошибку валидации Pydantic.
        
        Args:
            error: ValidationError от Pydantic
            event: Telegram событие
            user_id: ID пользователя
        """
        error_messages = "; ".join([err["msg"] for err in error.errors()])
        logger.warning(
            "Ошибка валидации Pydantic",
            event_type="pydantic_validation_error",
            user_id=user_id,
            errors=error_messages,
        )
        
        user_message = f"Ошибка валидации: {error_messages}. Попробуйте ещё раз."
        await self._send_error_message(event, user_message)
    
    async def _handle_value_error(
        self,
        error: ValueError,
        event: TelegramObject,
        user_id: int | None,
    ) -> None:
        """Обработать ValueError.
        
        Args:
            error: ValueError
            event: Telegram событие
            user_id: ID пользователя
        """
        logger.warning(
            "Ошибка валидации (ValueError)",
            event_type="value_error",
            user_id=user_id,
            error=str(error),
        )
        
        await self._send_error_message(event, str(error))
    
    async def _handle_telegram_error(
        self,
        error: TelegramBadRequest,
        event: TelegramObject,
        user_id: int | None,
    ) -> None:
        """Обработать ошибку Telegram BadRequest.
        
        Args:
            error: TelegramBadRequest
            event: Telegram событие
            user_id: ID пользователя
        """
        error_msg = str(error).lower()
        
        # "message is not modified" - не критичная ошибка, просто логируем
        if "message is not modified" in error_msg:
            logger.debug(
                "Сообщение не изменилось (Telegram)",
                event_type="telegram_message_not_modified",
                user_id=user_id,
            )
            return
        
        # Другие ошибки Telegram логируем как предупреждения
        logger.warning(
            "Ошибка Telegram BadRequest",
            event_type="telegram_bad_request",
            user_id=user_id,
            error=str(error),
        )
    
    async def _handle_telegram_api_error(
        self,
        error: TelegramAPIError,
        event: TelegramObject,
        user_id: int | None,
    ) -> None:
        """Обработать ошибку Telegram API.
        
        Args:
            error: TelegramAPIError
            event: Telegram событие
            user_id: ID пользователя
        """
        logger.error(
            "Ошибка Telegram API",
            event_type="telegram_api_error",
            user_id=user_id,
            error=str(error),
            exc_info=True,
        )
        
        user_message = "Произошла ошибка при взаимодействии с Telegram. Попробуйте позже."
        await self._send_error_message(event, user_message)
    
    async def _handle_unexpected_error(
        self,
        error: Exception,
        event: TelegramObject,
        user_id: int | None,
    ) -> None:
        """Обработать неожиданную ошибку.
        
        Args:
            error: Неожиданное исключение
            event: Telegram событие
            user_id: ID пользователя
        """
        logger.error(
            "Неожиданная ошибка в handler",
            event_type="unexpected_error",
            user_id=user_id,
            error_type=type(error).__name__,
            error=str(error),
            exc_info=True,
        )
        
        await self._send_error_message(event, ErrorMessages.GENERIC_ERROR)
    
    async def _send_error_message(
        self,
        event: TelegramObject,
        message: str,
    ) -> None:
        """Отправить сообщение об ошибке пользователю.
        
        Args:
            event: Telegram событие
            message: Текст сообщения
        """
        try:
            if isinstance(event, Message):
                await event.answer(message)
            elif isinstance(event, CallbackQuery):
                # Для CallbackQuery отправляем сообщение и отвечаем на callback
                await event.message.answer(message)
                await event.answer()
        except Exception as e:
            # Если не удалось отправить сообщение, логируем ошибку
            logger.error(
                "Не удалось отправить сообщение об ошибке",
                event_type="error_message_send_failed",
                error=str(e),
                exc_info=True,
            )
