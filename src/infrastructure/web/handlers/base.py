"""Базовый класс для обработчиков с общей логикой обработки ошибок."""
import functools
from typing import Callable, Any, TypeVar, Awaitable
import structlog
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from pydantic import ValidationError

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class BaseHandler:
    """Базовый класс для обработчиков с общей логикой обработки ошибок и декораторами."""
    
    @staticmethod
    def get_user_id(event: Message | CallbackQuery) -> int:
        """
        Получить ID пользователя из события.
        
        Args:
            event: Message или CallbackQuery
            
        Returns:
            ID пользователя
        """
        return event.from_user.id
    
    @staticmethod
    async def handle_validation_error(
        error: ValidationError,
        user_id: int,
        event: Message | CallbackQuery,
        error_message: str | None = None,
    ) -> None:
        """
        Обработать ошибку валидации Pydantic.
        
        Args:
            error: ValidationError от Pydantic
            user_id: ID пользователя
            event: Message или CallbackQuery для отправки ответа
            error_message: Кастомное сообщение об ошибке (опционально)
        """
        error_messages = "; ".join([err["msg"] for err in error.errors()])
        logger.warning(
            "Ошибка валидации данных",
            event_type="validation_error",
            user_id=user_id,
            errors=error_messages,
        )
        
        message = error_message or f"Ошибка валидации: {error_messages}. Попробуйте еще раз."
        
        if isinstance(event, Message):
            await event.answer(message)
        else:
            await event.message.answer(message)
            await event.answer()
    
    @staticmethod
    async def handle_value_error(
        error: ValueError,
        user_id: int,
        event: Message | CallbackQuery,
        error_message: str | None = None,
    ) -> None:
        """
        Обработать ошибку ValueError.
        
        Args:
            error: ValueError
            user_id: ID пользователя
            event: Message или CallbackQuery для отправки ответа
            error_message: Кастомное сообщение об ошибке (опционально)
        """
        logger.warning(
            "Ошибка валидации",
            event_type="value_error",
            user_id=user_id,
            error=str(error),
        )
        
        message = error_message or str(error)
        
        if isinstance(event, Message):
            await event.answer(message)
        else:
            await event.message.answer(message)
            await event.answer()
    
    @staticmethod
    async def handle_generic_error(
        error: Exception,
        user_id: int,
        event: Message | CallbackQuery,
        handler_name: str,
        error_message: str = "Произошла непредвиденная ошибка.",
    ) -> None:
        """
        Обработать общую ошибку.
        
        Args:
            error: Exception
            user_id: ID пользователя
            event: Message или CallbackQuery для отправки ответа
            handler_name: Имя обработчика для логирования
            error_message: Сообщение для пользователя
        """
        logger.error(
            f"Ошибка в {handler_name}",
            event_type="handler_error",
            user_id=user_id,
            handler=handler_name,
            error=str(error),
            exc_info=True,
        )
        
        if isinstance(event, Message):
            await event.answer(error_message)
        else:
            await event.message.answer(error_message)
            await event.answer()
    
    @staticmethod
    def error_handler(
        default_error_message: str = "Произошла ошибка.",
        handle_validation: bool = True,
        handle_value_error: bool = True,
    ) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T | None]]]:
        """
        Декоратор для автоматической обработки ошибок в обработчиках.
        
        Args:
            default_error_message: Сообщение по умолчанию для пользователя
            handle_validation: Обрабатывать ли ValidationError
            handle_value_error: Обрабатывать ли ValueError
            
        Returns:
            Декорированная функция
        """
        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T | None]]:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T | None:
                # Ищем Message или CallbackQuery в аргументах
                event: Message | CallbackQuery | None = None
                for arg in args:
                    if isinstance(arg, (Message, CallbackQuery)):
                        event = arg
                        break
                
                if not event:
                    for value in kwargs.values():
                        if isinstance(value, (Message, CallbackQuery)):
                            event = value
                            break
                
                if not event:
                    # Если не нашли событие, просто вызываем функцию
                    return await func(*args, **kwargs)
                
                user_id = BaseHandler.get_user_id(event)
                handler_name = func.__name__
                
                try:
                    return await func(*args, **kwargs)
                except ValidationError as e:
                    if handle_validation:
                        await BaseHandler.handle_validation_error(e, user_id, event)
                        return None
                    raise
                except ValueError as e:
                    if handle_value_error:
                        await BaseHandler.handle_value_error(e, user_id, event)
                        return None
                    raise
                except Exception as e:
                    await BaseHandler.handle_generic_error(
                        e, user_id, event, handler_name, default_error_message
                    )
                    return None
            
            return wrapper
        return decorator
    
    @staticmethod
    async def safe_edit_text(
        callback: CallbackQuery,
        text: str,
        reply_markup: Any = None,
    ) -> None:
        """
        Безопасное редактирование текста сообщения с обработкой ошибки 'message is not modified'.
        
        Args:
            callback: CallbackQuery для редактирования
            text: Новый текст сообщения
            reply_markup: Клавиатура (опционально)
        """
        try:
            await callback.message.edit_text(text, reply_markup=reply_markup)
            logger.debug(
                "Сообщение успешно отредактировано",
                user_id=callback.from_user.id,
            )
        except TelegramBadRequest as e:
            error_msg = str(e).lower()
            if "message is not modified" in error_msg:
                logger.debug(
                    "Сообщение не изменилось",
                    user_id=callback.from_user.id,
                )
            else:
                logger.error(
                    "TelegramBadRequest при редактировании сообщения",
                    user_id=callback.from_user.id,
                    error=str(e),
                )
                raise
        except Exception as e:
            logger.error(
                "Неожиданная ошибка при редактировании сообщения",
                user_id=callback.from_user.id,
                error=str(e),
                exc_info=True,
            )
            raise
    
    @staticmethod
    async def safe_callback_answer(
        callback: CallbackQuery,
        text: str | None = None,
        show_alert: bool = False,
    ) -> None:
        """
        Безопасный ответ на callback query с обработкой устаревших запросов.
        
        Args:
            callback: CallbackQuery для ответа
            text: Текст ответа (опционально)
            show_alert: Показывать ли alert (опционально)
        """
        try:
            await callback.answer(text=text, show_alert=show_alert)
        except TelegramBadRequest as e:
            error_msg = str(e).lower()
            if "query is too old" in error_msg or "query id is invalid" in error_msg:
                logger.debug(
                    "Callback query устарел, игнорируем",
                    user_id=callback.from_user.id,
                )
            else:
                logger.warning(
                    "TelegramBadRequest при ответе на callback",
                    user_id=callback.from_user.id,
                    error=str(e),
                )
        except Exception as e:
            logger.warning(
                "Ошибка при ответе на callback",
                user_id=callback.from_user.id,
                error=str(e),
            )
