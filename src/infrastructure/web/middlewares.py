import os
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from src.application.repositories import IUserRepository

# Dependency injection placeholder
user_repository: IUserRepository = None  # type: ignore


class RegistrationCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        if user_repository is None:
            raise ValueError("UserRepository is not initialized in middleware")

        user_id = event.from_user.id

        # Allow /start command and registration related callbacks/messages to pass through
        if isinstance(event, Message) and (
            event.text == "/start"
            or data.get("fsm_state") == "RegistrationStates:waiting_for_description"
        ):
            return await handler(event, data)
        elif isinstance(event, CallbackQuery) and (
            event.data == "register_request" or event.data.startswith("admin_")
        ):
            return await handler(event, data)

        ADMIN_IDS = [
            int(admin_id.strip())
            for admin_id in os.environ.get("ADMIN_ID", "").split(",")
            if admin_id.strip()
        ]
        if user_id in ADMIN_IDS:
            return await handler(event, data)

        user = await user_repository.get_by_telegram_id(user_id)

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
