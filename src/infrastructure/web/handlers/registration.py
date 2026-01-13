# ruff: noqa: F821
import logging
import os
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


logger = logging.getLogger(__name__)

router = Router()

ADMIN_IDS = [int(admin_id.strip()) for admin_id in os.environ.get("ADMIN_ID", "").split(',') if admin_id.strip()]

class RegistrationStates(StatesGroup):
    waiting_for_description = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    try:
        user_telegram_id = message.from_user.id
        user = await user_repository.get_by_telegram_id(user_telegram_id)

        if user and user.is_registered:
            logger.info(f"Пользователь {user_telegram_id} уже зарегистрирован и использовал /start.")
            await message.answer(f"С возвращением, {message.from_user.full_name}! Вы уже зарегистрированы.")
        elif user and not user.is_registered:
            logger.info(f"Пользователь {user_telegram_id} ожидает одобрения администратора и использовал /start.")
            await message.answer("Ваш запрос на регистрацию ожидает одобрения администратором.")
        else:
            logger.info(f"Новый пользователь {user_telegram_id} использовал /start. Запрос на регистрацию.")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Зарегистрироваться", callback_data="register_request")]
            ])
            await message.answer(
                f"Привет, {message.from_user.full_name}! Я бот для логирования тренировок. Чтобы начать, пожалуйста, зарегистрируйтесь.",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка в cmd_start для пользователя {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке команды /start.")


@router.callback_query(F.data == "register_request")
async def process_register_request(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        logger.info(f"Пользователь {callback.from_user.id} инициировал запрос на регистрацию.")
        await callback.message.edit_text("Пожалуйста, расскажите немного о себе, чтобы администратор мог одобрить вашу заявку.")
        await state.set_state(RegistrationStates.waiting_for_description)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в process_register_request для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при начале регистрации.")
        await callback.answer()


@router.message(RegistrationStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext, bot: Bot) -> None:
    try:
        user_id = message.from_user.id
        username = message.from_user.username if message.from_user.username else ""
        first_name = message.from_user.first_name if message.from_user.first_name else ""
        last_name = message.from_user.last_name if message.from_user.last_name else ""
        description = message.text

        logger.info(f"Пользователь {user_id} отправил описание для регистрации.")
        success = await registration_use_case.request_registration(user_id, username, first_name, last_name, description)

        if success:
            await message.answer("Ваш запрос на регистрацию отправлен администратору и ожидает одобрения.")
            admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Одобрить", callback_data=f"admin_approve_{user_id}"),
                    InlineKeyboardButton(text="Отклонить", callback_data=f"admin_reject_{user_id}")
                ]
            ])
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"Новый запрос на регистрацию от @{username} ({first_name} {last_name}, ID: {user_id}).\nОписание: {description}",
                        reply_markup=admin_keyboard
                    )
                    logger.info(f"Администратор {admin_id} уведомлён о новом запросе на регистрацию от пользователя {user_id}.")
                except Exception as e:
                    logger.error(f"Не удалось уведомить администратора {admin_id} о регистрации пользователя {user_id}: {e}", exc_info=True)
        else:
            await message.answer("Ошибка при отправке запроса на регистрацию. Возможно, вы уже отправляли запрос.")
            logger.warning(f"Запрос на регистрацию для пользователя {user_id} не удался, возможно дубликат.")

    except Exception as e:
        logger.error(f"Ошибка в process_description для пользователя {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке вашего описания.")
    finally:
        await state.clear()


@router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve_request(callback: CallbackQuery, bot: Bot) -> None:
    try:
        if callback.from_user.id not in ADMIN_IDS:
            logger.warning(f"Не-администратор {callback.from_user.id} попытался одобрить регистрацию.")
            await callback.answer("У вас нет прав для выполнения этой операции.", show_alert=True)
            return

        user_id_str = callback.data.split('_')[-1]
        user_id = int(user_id_str)

        logger.info(f"Администратор {callback.from_user.id} пытается одобрить регистрацию для пользователя {user_id}.")
        success = await registration_use_case.approve_registration(user_id)

        if success:
            await callback.message.edit_text(f"Запрос от пользователя {user_id} одобрен.")
            try:
                await bot.send_message(chat_id=user_id, text="Ваша регистрация одобрена! Теперь вы можете пользоваться ботом.")
                logger.info(f"Пользователь {user_id} уведомлён об одобренной регистрации.")
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя {user_id} об одобренной регистрации: {e}", exc_info=True)
        else:
            await callback.message.edit_text(f"Ошибка при одобрении запроса от пользователя {user_id}. Возможно, он уже зарегистрирован или запрос не найден.")
            logger.warning(f"Администратор не смог одобрить регистрацию для пользователя {user_id}.")
    except Exception as e:
        logger.error(f"Ошибка в admin_approve_request для администратора {callback.from_user.id}, целевой пользователь {user_id_str}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при одобрении запроса.")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_request(callback: CallbackQuery, bot: Bot) -> None:
    try:
        if callback.from_user.id not in ADMIN_IDS:
            logger.warning(f"Не-администратор {callback.from_user.id} попытался отклонить регистрацию.")
            await callback.answer("У вас нет прав для выполнения этой операции.", show_alert=True)
            return

        user_id_str = callback.data.split('_')[-1]
        user_id = int(user_id_str)

        logger.info(f"Администратор {callback.from_user.id} пытается отклонить регистрацию для пользователя {user_id}.")
        success = await registration_use_case.reject_registration(user_id)

        if success:
            await callback.message.edit_text(f"Запрос от пользователя {user_id} отклонен.")
            try:
                await bot.send_message(chat_id=user_id, text="Ваша регистрация отклонена.")
                logger.info(f"Пользователь {user_id} уведомлён об отклонённой регистрации.")
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя {user_id} об отклонённой регистрации: {e}", exc_info=True)
        else:
            await callback.message.edit_text(f"Ошибка при отклонении запроса от пользователя {user_id}. Возможно, запрос уже обработан или не найден.")
            logger.warning(f"Администратор не смог отклонить регистрацию для пользователя {user_id}.")
    except Exception as e:
        logger.error(f"Ошибка в admin_reject_request для администратора {callback.from_user.id}, целевой пользователь {user_id_str}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при отклонении запроса.")
    finally:
        await callback.answer()