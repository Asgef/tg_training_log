"""Middleware для глобальной обработки ошибок."""
from typing import Callable, Dict, Any, Awaitable, Optional
import structlog
import rollbar
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from pydantic import ValidationError as PydanticValidationError

from src.configs.config import config
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
    
    def __init__(self):
        """Инициализация middleware."""
        super().__init__()
        self._current_data: Optional[Dict[str, Any]] = None
    
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
        # Сохраняем data для использования в методах обработки ошибок
        self._current_data = data
        
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
        finally:
            # Очищаем data после обработки для предотвращения утечек
            self._current_data = None
    
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
        
        # Отправляем в Rollbar
        self._report_to_rollbar(
            error=error,
            user_id=user_id,
            event_type="telegram_api_error",
            level="error",
            data=self._current_data,
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
        
        # Отправляем в Rollbar
        self._report_to_rollbar(
            error=error,
            user_id=user_id,
            event_type="unexpected_error",
            level="error",
            extra_data={"error_type": type(error).__name__},
            data=self._current_data,
        )
        
        await self._send_error_message(event, ErrorMessages.GENERIC_ERROR)
    
    def _report_to_rollbar(
        self,
        error: Exception,
        user_id: Optional[int],
        event_type: str,
        level: str = "error",
        extra_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Отправить ошибку в Rollbar для мониторинга.
        
        Args:
            error: Исключение для отправки
            user_id: ID пользователя (будет замаскирован)
            event_type: Тип события для классификации
            level: Уровень ошибки (error, warning, critical)
            extra_data: Дополнительные данные для контекста
            data: Данные из middleware (для получения correlation_id, update_id)
        """
        if not config.rollbar_token:
            return  # Rollbar не настроен, пропускаем
        
        try:
            # Получаем контекст из data или structlog contextvars
            correlation_id: Optional[str] = None
            update_id: Optional[int] = None
            
            if data:
                correlation_id = data.get("correlation_id")
                update_id = data.get("log_update_id")
            else:
                # Пытаемся получить из structlog contextvars
                try:
                    context = structlog.contextvars.get_contextvars()
                    correlation_id = context.get("correlation_id")
                    update_id = context.get("update_id")
                except Exception:
                    pass
            
            # Маскируем user_id (оставляем последние 4 цифры)
            masked_user_id: Optional[str] = None
            if user_id:
                user_id_str = str(user_id)
                if len(user_id_str) > 4:
                    masked_user_id = "*" * (len(user_id_str) - 4) + user_id_str[-4:]
                else:
                    masked_user_id = "*" * len(user_id_str)
            
            # Формируем payload для Rollbar
            payload_data: Dict[str, Any] = {
                "event_type": event_type,
            }
            
            if masked_user_id:
                payload_data["user_id"] = masked_user_id
            if correlation_id:
                payload_data["correlation_id"] = correlation_id
            if update_id:
                payload_data["update_id"] = update_id
            if extra_data:
                payload_data.update(extra_data)
            
            # Отправляем в Rollbar
            # Примечания:
            # 1. Rollbar SDK не бросает исключение при rate limit - только логирует предупреждение
            #    Проверяйте логи на наличие "Rollbar: over rate limit, data was dropped."
            # 2. Rollbar запускает фоновую задачу для отправки, поэтому исключения (например, ConnectTimeout)
            #    могут возникнуть в фоновой задаче. Они обрабатываются через event loop exception handler
            #    в main.py (_rollbar_task_exception_handler)
            # 3. Таймаут для HTTP запросов настроен в rollbar.init(timeout=15) в main.py
            rollbar.report_exc_info(
                exc_info=(type(error), error, error.__traceback__),
                level=level,
                request_data=payload_data,
            )
            
            # Логируем попытку отправки (сам Rollbar может отбросить из-за rate limit или таймаута)
            logger.debug(
                "Попытка отправки ошибки в Rollbar",
                event_type="rollbar_report_attempted",
                error_type=type(error).__name__,
                event_type_reported=event_type,
                user_id=masked_user_id,
                correlation_id=correlation_id,
                update_id=update_id,
            )
        except Exception as rollbar_error:
            # Если Rollbar сам упал, логируем, но не прерываем выполнение
            logger.error(
                "Не удалось отправить ошибку в Rollbar",
                event_type="rollbar_report_failed",
                rollbar_error=str(rollbar_error),
                original_error=str(error),
                exc_info=True,
            )
    
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
