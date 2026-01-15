"""Middleware для проверки регистрации пользователей."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from src.application.repositories import IUserRepository
from src.configs.config import config


class RegistrationCheckMiddleware(BaseMiddleware):
    """Middleware для проверки регистрации пользователя.
    
    Проверяет зарегистрирован ли пользователь перед выполнением handler.
    Пропускает команду /start и callback для регистрации.
    """
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события с проверкой регистрации.
        
        Args:
            handler: Следующий handler в цепочке
            event: Telegram событие
            data: Данные для передачи в handler
            
        Returns:
            Результат выполнения handler или None если пользователь не зарегистрирован
        """
        # Получаем user_repository из data (инъектируется DependencyInjectionMiddleware)
        user_repository: IUserRepository = data.get("user_repository")
        if user_repository is None:
            raise ValueError("UserRepository не инициализирован в middleware")

        user_id = event.from_user.id

        # Разрешить команду /start и связанные с регистрацией callback
        if isinstance(event, Message) and event.text == "/start":
            return await handler(event, data)
        elif isinstance(event, CallbackQuery) and (
            event.data == "register_request" or event.data.startswith("admin_")
        ):
            return await handler(event, data)
        
        # Разрешить все сообщения в FSM состоянии регистрации
        # (handler с декоратором state filter сам проверит состояние)
        fsm_context = data.get("state")
        if fsm_context:
            current_state = await fsm_context.get_state()
            if current_state and current_state.startswith("RegistrationStates:"):
                return await handler(event, data)

        # Админы могут пропустить проверку
        if user_id in config.admin_ids:
            return await handler(event, data)

        # Проверяем регистрацию пользователя
        user = await user_repository.get_by_telegram_id(user_id)

        if user and user.is_registered:
            return await handler(event, data)
        else:
            # Пользователь не зарегистрирован
            if isinstance(event, Message):
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Зарегистрироваться",
                                callback_data="register_request",
                            )
                        ]
                    ]
                )
                await event.answer(
                    "Для использования бота вам необходимо зарегистрироваться.",
                    reply_markup=keyboard,
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "Для использования бота вам необходимо зарегистрироваться.",
                    show_alert=True,
                )
            return
