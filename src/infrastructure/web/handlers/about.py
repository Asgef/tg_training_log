"""Handler для раздела справки."""
import structlog
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.use_case_interfaces import IWorkoutUseCase, IMachineManagementUseCase
from src.infrastructure.web.handlers.base import BaseHandler

logger = structlog.get_logger(__name__)

router = Router()


async def _edit_or_send_message(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """
    Редактирует сообщение или отправляет новое, если редактирование невозможно.
    """
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        await callback.answer()
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "message is not modified" in error_msg:
            # Сообщение не изменилось, просто отвечаем на callback
            await callback.answer()
        elif "message can't be edited" in error_msg or "message to edit not found" in error_msg:
            # Сообщение нельзя отредактировать, отправляем новое
            logger.debug(
                "Не удалось отредактировать сообщение справки, отправляем новое",
                user_id=callback.from_user.id,
                error=str(e),
            )
            await callback.message.answer(text, reply_markup=reply_markup)
            await callback.answer()
        else:
            logger.warning(
                "Ошибка при редактировании сообщения справки",
                user_id=callback.from_user.id,
                error=str(e),
            )
            await callback.message.answer(text, reply_markup=reply_markup)
            await callback.answer()
    except Exception as e:
        logger.error(
            "Неожиданная ошибка при редактировании сообщения справки",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await callback.message.answer(text, reply_markup=reply_markup)
        await callback.answer()


def build_about_main_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру главной страницы справки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Быстрый старт", callback_data="about_quickstart"),
            InlineKeyboardButton(text="💪 Тренажёры", callback_data="about_machines"),
        ],
        [
            InlineKeyboardButton(text="🧾 Подходы и тренировки", callback_data="about_sets"),
            InlineKeyboardButton(text="📊 Google Таблица", callback_data="about_google_sheets"),
        ],
        [
            InlineKeyboardButton(text="🧠 Термины (RIR)", callback_data="about_terms"),
        ],
    ])


def build_about_quickstart_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру раздела 'Быстрый старт'."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить тренажёр", callback_data="about_action_add_machine"),
            InlineKeyboardButton(text="🏋️ Начать тренировку", callback_data="about_action_start_workout"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в справку", callback_data="about_main"),
        ],
    ])


def build_about_machines_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру раздела 'Тренажёры'."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📚 Добавить из библиотеки", callback_data="about_action_add_from_library"),
            InlineKeyboardButton(text="➕ Создать вручную", callback_data="about_action_create_manual"),
        ],
        [
            InlineKeyboardButton(text="🏋️ Мои тренажёры", callback_data="about_action_list_machines"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в справку", callback_data="about_main"),
        ],
    ])


def build_about_sets_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру раздела 'Подходы и тренировки'."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Записать подход", callback_data="about_action_record_set"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в справку", callback_data="about_main"),
        ],
    ])


def build_about_google_sheets_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру раздела 'Google Таблица'."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗 Подключить Google Таблицу", callback_data="about_action_setup_sheets"),
            InlineKeyboardButton(text="📤 Выгрузить данные", callback_data="about_action_export_sheets"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в справку", callback_data="about_main"),
        ],
    ])


def build_about_terms_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру раздела 'Термины (RIR)'."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Назад в справку", callback_data="about_main"),
        ],
    ])


ABOUT_MAIN_TEXT = """ℹ️ Справка

Этот бот помогает вести журнал тренировок:
• тренировки → тренажёры → подходы
• у тренажёров есть мышечные зоны и мышцы
• данные можно выгружать в Google Таблицу для графиков и анализа

Выбери раздел ниже."""


ABOUT_QUICKSTART_TEXT = """🚀 Быстрый старт

1) Добавь тренажёры (вручную или из библиотеки)
2) Нажми 🏋️ Начать тренировку
3) ➕ Записать подход → выбери тренажёр → укажи вес/повторы/RIR → сохрани
4) В конце нажми ✅ Завершить тренировку

Совет: библиотека тренажёров экономит время — там уже заполнены зоны и мышцы."""


ABOUT_MACHINES_TEXT = """🏋️ Тренажёры

Тренажёр в боте — это то, что ты выполняешь в зале (станок или упражнение).
Для каждого тренажёра можно указать:
• мышечные зоны (удобно)
• и/или конкретные мышцы (точно)

Можно добавить тренажёр из библиотеки — он создастся у тебя с готовой разметкой.
После добавления ты можешь изменить название, зоны и мышцы — это будет только твоё."""


ABOUT_SETS_TEXT = """🧾 Подходы и тренировки

Подходы записываются только внутри тренировки.

Во время активной тренировки доступны:
• ➕ Записать подход
• ✅ Завершить тренировку
• ❌ Отменить тренировку

Если в тренировке уже есть подходы, при отмене бот попросит подтверждение."""


ABOUT_GOOGLE_SHEETS_TEXT = """📊 Google Таблица

Ты можешь подключить свою Google Таблицу и выгружать туда данные для графиков и анализа.

Что выгружается:
• журнал подходов
• датасет нагрузки по мышцам
• справочник тренажёров
• справочники зон и мышц

Логи добавляются вниз — история сохраняется.
Если доступов к таблице не хватает, бот подскажет, какой доступ выдать."""


ABOUT_TERMS_TEXT = """🧠 Термины: RIR

RIR (Reps In Reserve) — сколько повторов осталось "в запасе".

Примеры:
• RIR 0 — отказ (больше не повторишь)
• RIR 1 — мог бы сделать ещё 1 повтор
• RIR 2 — мог бы сделать ещё 2 повтора

RIR помогает контролировать нагрузку без постоянных тренировок в отказ."""


@router.message(F.text == "ℹ️ Справка")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при открытии справки.")
async def handle_about_button(message: Message) -> None:
    """Обработчик кнопки 'ℹ️ Справка' из главного меню."""
    user_id = BaseHandler.get_user_id(message)
    logger.info(
        "Пользователь открыл справку",
        event_type="about_opened",
        user_id=user_id,
        source="button",
    )
    keyboard = build_about_main_keyboard()
    await message.answer(ABOUT_MAIN_TEXT, reply_markup=keyboard)


@router.message(Command("about"))
@BaseHandler.error_handler(default_error_message="Произошла ошибка при открытии справки.")
async def cmd_about(message: Message) -> None:
    """Обработчик команды /about."""
    user_id = BaseHandler.get_user_id(message)
    logger.info(
        "Пользователь открыл справку",
        event_type="about_opened",
        user_id=user_id,
        source="command",
    )
    keyboard = build_about_main_keyboard()
    await message.answer(ABOUT_MAIN_TEXT, reply_markup=keyboard)


@router.callback_query(F.data == "about_main")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при переходе в справку.")
async def about_main_callback(callback: CallbackQuery) -> None:
    """Обработчик возврата к главной странице справки."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь вернулся к главной странице справки",
        event_type="about_main_viewed",
        user_id=user_id,
    )
    keyboard = build_about_main_keyboard()
    await _edit_or_send_message(callback, ABOUT_MAIN_TEXT, keyboard)


@router.callback_query(F.data == "about_quickstart")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при открытии раздела 'Быстрый старт'.")
async def about_quickstart_callback(callback: CallbackQuery) -> None:
    """Обработчик раздела 'Быстрый старт'."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь открыл раздел 'Быстрый старт'",
        event_type="about_quickstart_viewed",
        user_id=user_id,
    )
    keyboard = build_about_quickstart_keyboard()
    await _edit_or_send_message(callback, ABOUT_QUICKSTART_TEXT, keyboard)


@router.callback_query(F.data == "about_machines")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при открытии раздела 'Тренажёры'.")
async def about_machines_callback(callback: CallbackQuery) -> None:
    """Обработчик раздела 'Тренажёры'."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь открыл раздел 'Тренажёры'",
        event_type="about_machines_viewed",
        user_id=user_id,
    )
    keyboard = build_about_machines_keyboard()
    await _edit_or_send_message(callback, ABOUT_MACHINES_TEXT, keyboard)


@router.callback_query(F.data == "about_sets")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при открытии раздела 'Подходы и тренировки'.")
async def about_sets_callback(callback: CallbackQuery) -> None:
    """Обработчик раздела 'Подходы и тренировки'."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь открыл раздел 'Подходы и тренировки'",
        event_type="about_sets_viewed",
        user_id=user_id,
    )
    keyboard = build_about_sets_keyboard()
    await _edit_or_send_message(callback, ABOUT_SETS_TEXT, keyboard)


@router.callback_query(F.data == "about_google_sheets")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при открытии раздела 'Google Таблица'.")
async def about_google_sheets_callback(callback: CallbackQuery) -> None:
    """Обработчик раздела 'Google Таблица'."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь открыл раздел 'Google Таблица'",
        event_type="about_google_sheets_viewed",
        user_id=user_id,
    )
    keyboard = build_about_google_sheets_keyboard()
    await _edit_or_send_message(callback, ABOUT_GOOGLE_SHEETS_TEXT, keyboard)


@router.callback_query(F.data == "about_terms")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при открытии раздела 'Термины (RIR)'.")
async def about_terms_callback(callback: CallbackQuery) -> None:
    """Обработчик раздела 'Термины (RIR)'."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь открыл раздел 'Термины (RIR)'",
        event_type="about_terms_viewed",
        user_id=user_id,
    )
    keyboard = build_about_terms_keyboard()
    await _edit_or_send_message(callback, ABOUT_TERMS_TEXT, keyboard)


# Обработчики кнопок действий

@router.callback_query(F.data == "about_action_add_machine")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при открытии меню тренажёров.")
async def about_action_add_machine_callback(callback: CallbackQuery) -> None:
    """Обработчик кнопки 'Добавить тренажёр' из справки."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь нажал 'Добавить тренажёр' из справки",
        event_type="about_action_add_machine",
        user_id=user_id,
    )
    await callback.answer()
    # Импортируем здесь, чтобы избежать циклических импортов
    from src.infrastructure.web.handlers.machine.view import build_machines_menu_keyboard
    keyboard = build_machines_menu_keyboard()
    await callback.message.answer("Управление тренажерами:", reply_markup=keyboard)


@router.callback_query(F.data == "about_action_start_workout")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при начале тренировки.")
async def about_action_start_workout_callback(
    callback: CallbackQuery,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Обработчик кнопки 'Начать тренировку' из справки."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь нажал 'Начать тренировку' из справки",
        event_type="about_action_start_workout",
        user_id=user_id,
    )
    await callback.answer()
    
    try:
        session = await workout_use_case.start_new_workout(user_id)
        if session:
            logger.info(
                "Пользователь успешно начал тренировку из справки",
                event_type="workout_started",
                user_id=user_id,
                session_id=session.id,
                source="about",
            )
            from src.infrastructure.web.handlers.registration import build_main_menu
            await callback.message.answer(
                "Тренировка начата! Теперь вы можете записывать подходы.",
                reply_markup=build_main_menu(True),
            )
        else:
            logger.warning(
                "Пользователь не смог начать тренировку из справки; активная сессия уже существует",
                event_type="workout_start_failed",
                user_id=user_id,
                reason="active_session_exists",
                source="about",
            )
            await callback.message.answer("У вас уже есть активная тренировка. Завершите ее, прежде чем начинать новую.")
    except ValueError as e:
        logger.warning(
            "Пользователь не может начать тренировку из справки",
            event_type="workout_start_validation_error",
            user_id=user_id,
            error=str(e),
            source="about",
        )
        await callback.message.answer(str(e))
    except Exception as e:
        logger.error(
            "Ошибка при начале тренировки из справки",
            event_type="workout_start_error",
            user_id=user_id,
            error=str(e),
            source="about",
            exc_info=True,
        )
        await callback.message.answer("Произошла ошибка при начале тренировки.")


@router.callback_query(F.data == "about_action_add_from_library")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при открытии библиотеки тренажёров.")
async def about_action_add_from_library_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Обработчик кнопки 'Добавить из библиотеки' из справки."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь нажал 'Добавить из библиотеки' из справки",
        event_type="about_action_add_from_library",
        user_id=user_id,
    )
    await callback.answer()
    # Отправляем сообщение с кнопкой для открытия библиотеки
    from src.infrastructure.web.handlers.machine.keyboards import build_library_start_menu_keyboard
    keyboard = build_library_start_menu_keyboard()
    await callback.message.answer(
        "➕ Добавить тренажёр из библиотеки\nВыберите действие:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "about_action_create_manual")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при создании тренажёра.")
async def about_action_create_manual_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Обработчик кнопки 'Создать вручную' из справки."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь нажал 'Создать вручную' из справки",
        event_type="about_action_create_manual",
        user_id=user_id,
    )
    await callback.answer()
    # Отправляем сообщение для начала создания тренажёра
    from src.infrastructure.web.handlers.machine.states import MachineStates
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_machine_creation")]
    ])
    await callback.message.answer(
        "Введите название нового тренажера:",
        reply_markup=cancel_keyboard,
    )
    await state.set_state(MachineStates.waiting_for_machine_name)


@router.callback_query(F.data == "about_action_list_machines")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при получении списка тренажёров.")
async def about_action_list_machines_callback(
    callback: CallbackQuery,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик кнопки 'Мои тренажёры' из справки."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь нажал 'Мои тренажёры' из справки",
        event_type="about_action_list_machines",
        user_id=user_id,
    )
    await callback.answer()
    # Получаем список тренажёров и показываем его
    machines = await machine_management_use_case.get_user_machines(user_id)
    
    if not machines:
        logger.info(
            "Пользователь запросил список тренажёров из справки, ничего не найдено",
            event_type="machines_list_empty",
            user_id=user_id,
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="machines_menu")]
        ])
        await callback.message.answer("У вас пока нет добавленных тренажеров.", reply_markup=keyboard)
        return
    
    text = "Ваши тренажеры:\n"
    for machine in machines:
        text += f"ID: {machine.id}, Название: {machine.name}\n"
    
    from src.infrastructure.web.handlers.machine.keyboards import KeyboardBuilder
    keyboard = KeyboardBuilder.build_machine_list_keyboard(machines)
    await callback.message.answer(text, reply_markup=keyboard)
    logger.info(
        "Пользователь просмотрел список тренажёров из справки",
        event_type="machines_list_viewed",
        user_id=user_id,
        machines_count=len(machines),
    )


@router.callback_query(F.data == "about_action_record_set")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при записи подхода.")
async def about_action_record_set_callback(
    callback: CallbackQuery,
    workout_use_case: IWorkoutUseCase,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик кнопки 'Записать подход' из справки."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь нажал 'Записать подход' из справки",
        event_type="about_action_record_set",
        user_id=user_id,
    )
    await callback.answer()
    
    # Проверяем наличие активной тренировки
    active_session = await workout_use_case.get_active_workout_session(user_id)
    if not active_session:
        await callback.message.answer(
            "Для записи подхода необходимо начать тренировку. "
            "Используйте кнопку '🏋️ Начать тренировку' в главном меню для записи подхода."
        )
        return
    
    # Если тренировка активна, вызываем команду записи подхода
    from src.infrastructure.web.handlers.workout import cmd_record_set
    from aiogram.types import Message
    
    # Создаём временное сообщение для вызова команды
    # Но проще показать сообщение с инструкцией
    await callback.message.answer(
        "Используйте кнопку '📝 Записать подход' в главном меню для записи подхода."
    )


@router.callback_query(F.data == "about_action_setup_sheets")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при настройке Google Sheets.")
async def about_action_setup_sheets_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Обработчик кнопки 'Подключить Google Таблицу' из справки."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь нажал 'Подключить Google Таблицу' из справки",
        event_type="about_action_setup_sheets",
        user_id=user_id,
    )
    await callback.answer()
    # Вызываем callback для настройки Google Sheets
    from src.infrastructure.web.handlers.common import setup_google_sheets_callback
    await setup_google_sheets_callback(callback, state)


@router.callback_query(F.data == "about_action_export_sheets")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при экспорте данных.")
async def about_action_export_sheets_callback(
    callback: CallbackQuery,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Обработчик кнопки 'Выгрузить данные' из справки."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь нажал 'Выгрузить данные' из справки",
        event_type="about_action_export_sheets",
        user_id=user_id,
    )
    await callback.answer()
    # Вызываем callback для экспорта данных
    from src.infrastructure.web.handlers.common import export_data_to_sheets_callback
    await export_data_to_sheets_callback(callback, db_session_factory)
