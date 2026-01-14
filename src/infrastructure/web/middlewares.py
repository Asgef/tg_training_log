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

# Заглушка для dependency injection
user_repository: IUserRepository = None  # type: ignore


class RegistrationCheckMiddleware(BaseMiddleware):
    user_repository: IUserRepository = None  # type: ignore
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        repo = self.user_repository or user_repository
        if repo is None:
            raise ValueError("UserRepository не инициализирован в middleware")

        user_id = event.from_user.id

        # Разрешить команду /start и связанные с регистрацией callback/сообщения
        if isinstance(event, Message) and (
            event.text == "/start"
            or data.get("fsm_state") == "RegistrationStates:waiting_for_description"
        ):
            return await handler(event, data)
        elif isinstance(event, CallbackQuery) and (
            event.data == "register_request" or event.data.startswith("admin_")
        ):
            return await handler(event, data)

        if user_id in config.admin_ids:
            return await handler(event, data)

        user = await repo.get_by_telegram_id(user_id)

        if user and user.is_registered:
            return await handler(event, data)
        else:
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
