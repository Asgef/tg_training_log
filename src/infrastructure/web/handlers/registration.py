"""Handler для регистрации пользователей."""
import structlog
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from pydantic import ValidationError

from src.configs.config import config
from src.application.use_case_interfaces import IRegistrationUseCase, IWorkoutUseCase
from src.application.dto import RegistrationInputDTO

logger = structlog.get_logger(__name__)

router = Router()

ADMIN_IDS = config.admin_ids


def build_main_menu(has_active_workout: bool) -> ReplyKeyboardMarkup:
    """Создает главное меню с кнопками для зарегистрированных пользователей."""
    workout_row = (
        [
            KeyboardButton(text="✅ Завершить тренировку"),
            KeyboardButton(text="❌ Отменить тренировку"),
        ]
        if has_active_workout
        else [KeyboardButton(text="🏋️ Начать тренировку")]
    )
    keyboard_rows: list[list[KeyboardButton]] = [workout_row]

    if has_active_workout:
        keyboard_rows.append(
            [
                KeyboardButton(text="📝 Записать подход"),
                KeyboardButton(text="💪 Тренажеры"),
            ]
        )
    else:
        keyboard_rows.append([KeyboardButton(text="💪 Тренажеры")])

    keyboard_rows.append([KeyboardButton(text="📊 Google Sheets")])

    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие из меню",
    )
    return keyboard

class RegistrationStates(StatesGroup):
    waiting_for_description = State()


@router.message(Command("start"))
async def cmd_start(
    message: Message,
    registration_use_case: IRegistrationUseCase,
    workout_use_case: IWorkoutUseCase,
    state: FSMContext = None,
) -> None:
    """Обработчик команды /start."""
    try:
        user_telegram_id = message.from_user.id
        user = await registration_use_case.get_user_by_telegram_id(user_telegram_id)

        if user and user.is_registered:
            has_active_workout = bool(
                await workout_use_case.get_active_workout_session(user_telegram_id)
            )
            logger.info(
                "Пользователь уже зарегистрирован и использовал /start",
                event_type="user_start_command",
                user_id=user_telegram_id,
                is_registered=True,
            )
            await message.answer(
                f"С возвращением, {message.from_user.full_name}! Вы уже зарегистрированы.",
                reply_markup=build_main_menu(has_active_workout),
            )
        elif user and not user.is_registered:
            logger.info(
                "Пользователь ожидает одобрения администратора",
                event_type="user_start_command",
                user_id=user_telegram_id,
                is_registered=False,
                registration_status="pending",
            )
            await message.answer("Ваш запрос на регистрацию ожидает одобрения администратором.")
        else:
            logger.info(
                "Новый пользователь использовал /start",
                event_type="user_start_command",
                user_id=user_telegram_id,
                is_registered=False,
                registration_status="not_started",
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Зарегистрироваться", callback_data="register_request")]
            ])
            await message.answer(
                f"Привет, {message.from_user.full_name}! Я бот для логирования тренировок. Чтобы начать, пожалуйста, зарегистрируйтесь.",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(
            "Ошибка в cmd_start",
            event_type="user_start_command_error",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await message.answer("Произошла ошибка при обработке команды /start.")


@router.callback_query(F.data == "register_request")
async def process_register_request(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        logger.info(
            "Пользователь инициировал запрос на регистрацию",
            event_type="registration_request_started",
            user_id=callback.from_user.id,
        )
        await callback.message.edit_text("Пожалуйста, представьтесь и расскажите немного о себе. Если вы понравитесь администратору то он вас одобрит.")
        await state.set_state(RegistrationStates.waiting_for_description)
        await callback.answer()
    except Exception as e:
        logger.error(
            "Ошибка в process_register_request",
            event_type="registration_request_error",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await callback.message.answer("Произошла ошибка при начале регистрации.")
        await callback.answer()


@router.message(RegistrationStates.waiting_for_description)
async def process_description(
    message: Message,
    state: FSMContext,
    bot: Bot,
    registration_use_case: IRegistrationUseCase,
) -> None:
    """Обработчик описания пользователя при регистрации."""
    try:
        user_id = message.from_user.id
        username = message.from_user.username if message.from_user.username else ""
        first_name = message.from_user.first_name if message.from_user.first_name else ""
        last_name = message.from_user.last_name if message.from_user.last_name else ""
        
        # Валидация через Pydantic DTO
        try:
            registration_input = RegistrationInputDTO(
                telegram_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                description=message.text,
            )
        except ValidationError as e:
            error_messages = "; ".join([err["msg"] for err in e.errors()])
            logger.warning(
                "Пользователь предоставил невалидные данные регистрации",
                event_type="registration_validation_error",
                user_id=user_id,
                errors=error_messages,
            )
            await message.answer(f"Ошибка валидации: {error_messages}. Попробуйте еще раз.")
            return

        logger.info(
            "Пользователь отправил описание для регистрации",
            event_type="registration_description_submitted",
            user_id=user_id,
            username=username,
        )
        success = await registration_use_case.request_registration(
            registration_input.telegram_id,
            registration_input.username,
            registration_input.first_name,
            registration_input.last_name,
            registration_input.description,
        )

        if success:
            logger.info(
                "Запрос на регистрацию успешно создан",
                event_type="registration_request_created",
                user_id=user_id,
                username=username,
            )
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
                        text=f"Новый запрос на регистрацию от @{username} ({first_name} {last_name}, ID: {user_id}).\nОписание: {registration_input.description}",
                        reply_markup=admin_keyboard
                    )
                    logger.info(
                        "Администратор уведомлён о новом запросе на регистрацию",
                        event_type="admin_notification_sent",
                        admin_id=admin_id,
                        user_id=user_id,
                    )
                except Exception as e:
                    logger.error(
                        "Не удалось уведомить администратора о регистрации",
                        event_type="admin_notification_error",
                        admin_id=admin_id,
                        user_id=user_id,
                        error=str(e),
                        exc_info=True,
                    )
        else:
            logger.warning(
                "Запрос на регистрацию не удался, возможно дубликат",
                event_type="registration_request_failed",
                user_id=user_id,
                reason="duplicate_or_error",
            )
            await message.answer("Ошибка при отправке запроса на регистрацию. Возможно, вы уже отправляли запрос.")

    except Exception as e:
        logger.error(
            "Ошибка в process_description",
            event_type="registration_description_error",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await message.answer("Произошла ошибка при обработке вашего описания.")
    finally:
        await state.clear()


@router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve_request(
    callback: CallbackQuery,
    bot: Bot,
    registration_use_case: IRegistrationUseCase,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Обработчик одобрения регистрации администратором."""
    try:
        if callback.from_user.id not in ADMIN_IDS:
            logger.warning(
                "Не-администратор попытался одобрить регистрацию",
                event_type="unauthorized_registration_approval_attempt",
                user_id=callback.from_user.id,
            )
            await callback.answer("У вас нет прав для выполнения этой операции.", show_alert=True)
            return

        user_id_str = callback.data.split('_')[-1]
        user_id = int(user_id_str)

        logger.info(
            "Администратор пытается одобрить регистрацию",
            event_type="registration_approval_started",
            admin_id=callback.from_user.id,
            target_user_id=user_id,
        )
        success = await registration_use_case.approve_registration(user_id)

        if success:
            logger.info(
                "Регистрация успешно одобрена",
                event_type="registration_approved",
                admin_id=callback.from_user.id,
                user_id=user_id,
            )
            await callback.message.edit_text(f"Запрос от пользователя {user_id} одобрен.")
            try:
                has_active_workout = bool(
                    await workout_use_case.get_active_workout_session(user_id)
                )
                await bot.send_message(
                    chat_id=user_id,
                    text="Ваша регистрация одобрена! Теперь вы можете пользоваться ботом.",
                    reply_markup=build_main_menu(has_active_workout),
                )
                logger.info(
                    "Пользователь уведомлён об одобренной регистрации",
                    event_type="user_notified_registration_approved",
                    user_id=user_id,
                )
            except Exception as e:
                logger.error(
                    "Не удалось уведомить пользователя об одобренной регистрации",
                    event_type="user_notification_error",
                    user_id=user_id,
                    error=str(e),
                    exc_info=True,
                )
        else:
            logger.warning(
                "Администратор не смог одобрить регистрацию",
                event_type="registration_approval_failed",
                admin_id=callback.from_user.id,
                user_id=user_id,
                reason="user_already_registered_or_not_found",
            )
            await callback.message.edit_text(f"Ошибка при одобрении запроса от пользователя {user_id}. Возможно, он уже зарегистрирован или запрос не найден.")
    except Exception as e:
        logger.error(
            "Ошибка в admin_approve_request",
            event_type="registration_approval_error",
            admin_id=callback.from_user.id,
            target_user_id=user_id_str,
            error=str(e),
            exc_info=True,
        )
        await callback.message.answer("Произошла ошибка при одобрении запроса.")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_request(
    callback: CallbackQuery,
    bot: Bot,
    registration_use_case: IRegistrationUseCase,
) -> None:
    """Обработчик отклонения регистрации администратором."""
    try:
        if callback.from_user.id not in ADMIN_IDS:
            logger.warning(
                "Не-администратор попытался отклонить регистрацию",
                event_type="unauthorized_registration_rejection_attempt",
                user_id=callback.from_user.id,
            )
            await callback.answer("У вас нет прав для выполнения этой операции.", show_alert=True)
            return

        user_id_str = callback.data.split('_')[-1]
        user_id = int(user_id_str)

        logger.info(
            "Администратор пытается отклонить регистрацию",
            event_type="registration_rejection_started",
            admin_id=callback.from_user.id,
            target_user_id=user_id,
        )
        success = await registration_use_case.reject_registration(user_id)

        if success:
            logger.info(
                "Регистрация успешно отклонена",
                event_type="registration_rejected",
                admin_id=callback.from_user.id,
                user_id=user_id,
            )
            await callback.message.edit_text(f"Запрос от пользователя {user_id} отклонен.")
            try:
                await bot.send_message(chat_id=user_id, text="Ваша регистрация отклонена.")
                logger.info(
                    "Пользователь уведомлён об отклонённой регистрации",
                    event_type="user_notified_registration_rejected",
                    user_id=user_id,
                )
            except Exception as e:
                logger.error(
                    "Не удалось уведомить пользователя об отклонённой регистрации",
                    event_type="user_notification_error",
                    user_id=user_id,
                    error=str(e),
                    exc_info=True,
                )
        else:
            logger.warning(
                "Администратор не смог отклонить регистрацию",
                event_type="registration_rejection_failed",
                admin_id=callback.from_user.id,
                user_id=user_id,
                reason="request_already_processed_or_not_found",
            )
            await callback.message.edit_text(f"Ошибка при отклонении запроса от пользователя {user_id}. Возможно, запрос уже обработан или не найден.")
    except Exception as e:
        logger.error(
            "Ошибка в admin_reject_request",
            event_type="registration_rejection_error",
            admin_id=callback.from_user.id,
            target_user_id=user_id_str,
            error=str(e),
            exc_info=True,
        )
        await callback.message.answer("Произошла ошибка при отклонении запроса.")
    finally:
        await callback.answer()


@router.message(Command("menu"))
async def cmd_menu(
    message: Message,
    registration_use_case: IRegistrationUseCase,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Показывает главное меню."""
    try:
        user_telegram_id = message.from_user.id
        is_registered = await registration_use_case.check_user_registered(user_telegram_id)
        
        if is_registered:
            has_active_workout = bool(
                await workout_use_case.get_active_workout_session(user_telegram_id)
            )
            await message.answer(
                "Главное меню:",
                reply_markup=build_main_menu(has_active_workout),
            )
        else:
            await message.answer("Для использования бота вам необходимо зарегистрироваться.")
    except Exception as e:
        logger.error(
            "Ошибка в cmd_menu",
            event_type="menu_command_error",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await message.answer("Произошла ошибка при отображении меню.")

