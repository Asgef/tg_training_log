"""Обработчики для библиотеки тренажёров."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from src.application.use_case_interfaces import IMachineLibraryUseCase
from src.infrastructure.web.handlers.machine.states import MachineStates
from src.infrastructure.web.handlers.machine.keyboards import (
    build_machine_library_list_keyboard,
    build_machine_library_details_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()


async def _show_library_list(
    target_message: Message,
    machine_library_use_case: IMachineLibraryUseCase,
    query: str,
) -> None:
    if query:
        machines = await machine_library_use_case.search_library_machines(query=query)
        title = f"Результаты поиска: «{query}»"
    else:
        machines = await machine_library_use_case.list_library_machines()
        title = "Библиотека тренажёров"

    if not machines:
        await target_message.answer("Ничего не найдено. Попробуйте другой запрос.")
        return

    text_lines = [title, "", "Выберите тренажёр:"]
    await target_message.answer(
        "\n".join(text_lines),
        reply_markup=build_machine_library_list_keyboard(machines),
    )


@router.callback_query(F.data == "add_machine_from_library")
async def start_library_flow(
    callback: CallbackQuery,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    """Старт выбора тренажёра из библиотеки."""
    await state.set_state(MachineStates.waiting_for_library_search_query)
    await state.update_data(library_last_query="")
    await callback.message.edit_text(
        "Введите название для поиска в библиотеке или отправьте пустое сообщение, чтобы увидеть список."
    )
    await callback.answer()


@router.message(MachineStates.waiting_for_library_search_query)
async def process_library_search_query(
    message: Message,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    query = (message.text or "").strip()
    await state.update_data(library_last_query=query)
    await _show_library_list(message, machine_library_use_case, query)


@router.callback_query(F.data == "library_search_again")
async def library_search_again(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.set_state(MachineStates.waiting_for_library_search_query)
    await callback.message.edit_text("Введите новый запрос для поиска в библиотеке.")
    await callback.answer()


@router.callback_query(F.data == "library_back_to_results")
async def library_back_to_results(
    callback: CallbackQuery,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    data = await state.get_data()
    query = (data.get("library_last_query") or "").strip()
    await _show_library_list(callback.message, machine_library_use_case, query)
    await callback.answer()


@router.callback_query(F.data.startswith("library_machine_"))
async def library_machine_details(
    callback: CallbackQuery,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    machine_library_id = int(callback.data.split("_")[-1])
    machine = await machine_library_use_case.get_library_machine_details(
        machine_library_id
    )
    if not machine:
        await callback.answer("Тренажёр не найден.", show_alert=True)
        return

    zones_str = ", ".join([z.name for z in machine.zones]) if machine.zones else "Не указаны"
    muscles_str = ", ".join([m.name for m in machine.muscles]) if machine.muscles else "Не указаны"
    text = (
        f"{machine.name_ru}\n\n"
        f"Зоны: {zones_str}\n"
        f"Мышцы: {muscles_str}"
    )
    if len(text) > 4096:
        text = (
            f"{machine.name_ru}\n\n"
            f"Зоны: {len(machine.zones)} шт.\n"
            f"Мышцы: {len(machine.muscles)} шт."
        )

    await callback.message.edit_text(
        text, reply_markup=build_machine_library_details_keyboard(machine_library_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("add_library_machine_"))
async def add_library_machine(
    callback: CallbackQuery,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    user_id = callback.from_user.id
    machine_library_id = int(callback.data.split("_")[-1])
    try:
        created = await machine_library_use_case.add_machine_from_library(
            user_id=user_id, machine_library_id=machine_library_id
        )
        await state.clear()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К меню тренажёров", callback_data="machines_menu")]
            ]
        )
        await callback.message.edit_text(
            f"Тренажёр '{created.name}' добавлен в ваши тренажёры.",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(
            "Ошибка при добавлении тренажёра из библиотеки %s для пользователя %s: %s",
            machine_library_id,
            user_id,
            e,
            exc_info=True,
        )
        await callback.message.answer("Произошла ошибка при добавлении тренажёра.")
    finally:
        await callback.answer()
