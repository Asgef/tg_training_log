"""Обработчики для просмотра тренажёров."""
import structlog
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.application.use_case_interfaces import IMachineManagementUseCase
from src.infrastructure.web.handlers.machine.keyboards import KeyboardBuilder
from src.infrastructure.web.handlers.base import BaseHandler

logger = structlog.get_logger(__name__)
router = Router()


def build_machines_menu_keyboard() -> InlineKeyboardMarkup:
    """Построить клавиатуру меню управления тренажёрами."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить из библиотеки", callback_data="add_machine_from_library")],
        [InlineKeyboardButton(text="Создать вручную", callback_data="add_machine_manual")],
        [InlineKeyboardButton(text="Мои тренажеры", callback_data="list_machines")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="machines_menu_back")]
    ])


@router.message(Command("machines"))
@BaseHandler.error_handler(default_error_message="Произошла ошибка при обработке команды /machines.")
async def cmd_machines(
    message: Message,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик команды /machines."""
    user_id = BaseHandler.get_user_id(message)
    logger.info(
        "Пользователь использовал команду /machines",
        event_type="machines_command",
        user_id=user_id,
    )
    keyboard = build_machines_menu_keyboard()
    await message.answer("Управление тренажерами:", reply_markup=keyboard)


@router.callback_query(F.data == "list_machines")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при получении списка тренажеров.")
async def list_machines_callback(
    callback: CallbackQuery,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик просмотра списка тренажёров."""
    user_id = BaseHandler.get_user_id(callback)
    machines = await machine_management_use_case.get_user_machines(user_id)

    if not machines:
        logger.info(
            "Пользователь запросил список тренажёров, ничего не найдено",
            event_type="machines_list_empty",
            user_id=user_id,
        )
        await callback.message.edit_text("У вас пока нет добавленных тренажеров.")
        await callback.answer()
        return

    text = "Ваши тренажеры:\n"
    for machine in machines:
        text += f"ID: {machine.id}, Название: {machine.name}\n"
    
    keyboard = KeyboardBuilder.build_machine_list_keyboard(machines)
    await callback.message.edit_text(text, reply_markup=keyboard)
    logger.info(
        "Пользователь просмотрел список тренажёров",
        event_type="machines_list_viewed",
        user_id=user_id,
        machines_count=len(machines),
    )
    await callback.answer()


@router.callback_query(F.data == "machines_menu")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при открытии меню тренажеров.")
async def machines_menu_callback(
    callback: CallbackQuery,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Возврат к меню управления тренажёрами."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь вернулся в меню управления тренажёрами",
        event_type="machines_menu_return",
        user_id=user_id,
    )
    keyboard = build_machines_menu_keyboard()
    await callback.message.edit_text("Управление тренажерами:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "machines_menu_back")
@BaseHandler.error_handler(default_error_message="Произошла ошибка при возврате из меню тренажеров.")
async def machines_menu_back_callback(
    callback: CallbackQuery,
) -> None:
    """Возврат из меню управления тренажёрами - убрать inline-клавиатуру."""
    user_id = BaseHandler.get_user_id(callback)
    logger.info(
        "Пользователь вернулся из меню управления тренажёрами",
        event_type="machines_menu_back",
        user_id=user_id,
    )
    # Редактируем сообщение, убирая inline-клавиатуру
    await callback.message.edit_text(
        "Используйте кнопки меню внизу экрана.",
        reply_markup=None
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_machine_"))
async def view_machine_details_callback(
    callback: CallbackQuery,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик просмотра деталей тренажёра."""
    user_id = callback.from_user.id
    machine_id = int(callback.data.split('_')[-1])

    try:
        machine = await machine_management_use_case.get_machine_details(user_id, machine_id)

        if not machine:
            logger.warning(f"Пользователь {user_id} попытался просмотреть несуществующий или неавторизованный тренажёр {machine_id}.")
            await callback.message.edit_text("Тренажер не найден или у вас нет к нему доступа.")
            await callback.answer()
            return

        zones_str = ", ".join([z.name for z in machine.zones]) if machine.zones else "Не указаны"
        muscles_str = ", ".join([m.name for m in machine.muscles]) if machine.muscles else "Не указаны"
        text = f"**{machine.name}**\n" \
               f"ID: {machine.id}\n" \
               f"Зоны: {zones_str}\n" \
               f"Мышцы: {muscles_str}\n" \
               f"Архивирован: {'Да' if machine.is_archived else 'Нет'}"
        
        keyboard = KeyboardBuilder.build_machine_details_keyboard(machine.id)
        await callback.message.edit_text(text, reply_markup=keyboard)
        logger.info(f"Пользователь {user_id} просмотрел детали тренажёра {machine_id}.")

    except Exception as e:
        logger.error(f"Ошибка в view_machine_details_callback для пользователя {user_id}, тренажёр {machine_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при получении деталей тренажера.")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("archive_machine_"))
async def archive_machine_callback(
    callback: CallbackQuery,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик архивации тренажёра."""
    user_id = callback.from_user.id
    machine_id = int(callback.data.split('_')[-1])

    try:
        success = await machine_management_use_case.archive_machine(user_id, machine_id)

        if success:
            await callback.message.edit_text(f"Тренажер {machine_id} успешно архивирован.")
            logger.info(f"Пользователь {user_id} успешно архивировал тренажёр {machine_id}.")
        else:
            await callback.message.edit_text(f"Не удалось архивировать тренажер {machine_id}. Возможно, он уже архивирован или не найден.")
            logger.warning(f"Пользователь {user_id} не смог архивировать тренажёр {machine_id}.")
    except Exception as e:
        logger.error(f"Ошибка в archive_machine_callback для пользователя {user_id}, тренажёр {machine_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при архивации тренажера.")
    finally:
        await callback.answer()


# Обработчик кнопки меню
@router.message(F.text == "💪 Тренажеры")
async def handle_machines_button(
    message: Message,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик кнопки 'Тренажеры'."""
    await cmd_machines(message, machine_management_use_case)
