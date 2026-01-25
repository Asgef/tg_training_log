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
    build_library_start_menu_keyboard,
    build_library_search_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()


async def _show_library_list(
    target_message: Message,
    machine_library_use_case: IMachineLibraryUseCase,
    query: str,
    page: int = 0,
    page_size: int = 10,
    use_edit: bool = False,
) -> None:
    """Показать список библиотечных тренажёров с пагинацией.
    
    Args:
        target_message: Сообщение для редактирования/ответа
        machine_library_use_case: Use case для работы с библиотекой
        query: Поисковый запрос (пустая строка для полного списка)
        page: Номер страницы (0-based)
        page_size: Размер страницы
        use_edit: Если True, использовать edit_text вместо answer
    """
    offset = page * page_size
    limit = page_size
    
    if query:
        machines = await machine_library_use_case.search_library_machines(
            query=query, limit=limit + 1, offset=offset
        )
        title = f"Результаты поиска: «{query}»"
    else:
        machines = await machine_library_use_case.list_library_machines(
            limit=limit + 1, offset=offset
        )
        title = "Библиотека тренажёров"

    if not machines:
        # Пустой список - показываем сообщение с кнопкой показать список
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Показать список", callback_data="library_show_list")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="machines_menu")],
        ])
        if use_edit:
            await target_message.edit_text("Ничего не найдено.", reply_markup=keyboard)
        else:
            await target_message.answer("Ничего не найдено.", reply_markup=keyboard)
        return

    # Проверяем, есть ли следующая страница
    has_next = len(machines) > page_size
    if has_next:
        machines = machines[:page_size]  # Убираем лишний элемент
    
    has_prev = page > 0

    text_lines = [title, "", "Выберите тренажёр:"]
    keyboard = build_machine_library_list_keyboard(
        machines, page=page, has_next=has_next, has_prev=has_prev
    )
    
    if use_edit:
        await target_message.edit_text("\n".join(text_lines), reply_markup=keyboard)
    else:
        await target_message.answer("\n".join(text_lines), reply_markup=keyboard)


@router.callback_query(F.data == "add_machine_from_library")
async def start_library_flow(
    callback: CallbackQuery,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    """Старт выбора тренажёра из библиотеки."""
    await state.clear()
    await callback.message.edit_text(
        "➕ Добавить тренажёр из библиотеки\nВыберите действие:",
        reply_markup=build_library_start_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "library_show_list")
async def library_show_list(
    callback: CallbackQuery,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    """Показать первую страницу списка библиотечных тренажёров."""
    await state.update_data(
        library_last_query="",
        library_page=0,
        library_is_search=False,
    )
    await _show_library_list(
        callback.message, machine_library_use_case, query="", page=0, use_edit=True
    )
    await callback.answer()


@router.callback_query(F.data == "library_start_search")
async def library_start_search(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать поиск - перейти в FSM состояние."""
    await state.set_state(MachineStates.waiting_for_library_search_query)
    await state.update_data(library_last_query="", library_page=0, library_is_search=True)
    await callback.message.edit_text(
        "Введите часть названия",
        reply_markup=build_library_search_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "library_cancel_search")
async def library_cancel_search(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Отменить поиск и вернуться к стартовому меню."""
    await state.clear()
    await callback.message.edit_text(
        "➕ Добавить тренажёр из библиотеки\nВыберите действие:",
        reply_markup=build_library_start_menu_keyboard(),
    )
    await callback.answer()


@router.message(MachineStates.waiting_for_library_search_query)
async def process_library_search_query(
    message: Message,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    """Обработать поисковый запрос."""
    query = (message.text or "").strip()
    await state.update_data(library_last_query=query, library_page=0)
    await _show_library_list(message, machine_library_use_case, query, page=0)


@router.callback_query(F.data == "library_list_page_prev")
async def library_list_page_prev(
    callback: CallbackQuery,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    """Перейти на предыдущую страницу списка."""
    data = await state.get_data()
    query = (data.get("library_last_query") or "").strip()
    current_page = data.get("library_page", 0)
    new_page = max(0, current_page - 1)
    await state.update_data(library_page=new_page)
    await _show_library_list(
        callback.message, machine_library_use_case, query, page=new_page, use_edit=True
    )
    await callback.answer()


@router.callback_query(F.data == "library_list_page_next")
async def library_list_page_next(
    callback: CallbackQuery,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    """Перейти на следующую страницу списка."""
    data = await state.get_data()
    query = (data.get("library_last_query") or "").strip()
    current_page = data.get("library_page", 0)
    new_page = current_page + 1
    await state.update_data(library_page=new_page)
    await _show_library_list(
        callback.message, machine_library_use_case, query, page=new_page, use_edit=True
    )
    await callback.answer()


@router.callback_query(F.data == "library_back_to_results")
async def library_back_to_results(
    callback: CallbackQuery,
    state: FSMContext,
    machine_library_use_case: IMachineLibraryUseCase,
) -> None:
    """Вернуться к списку результатов."""
    data = await state.get_data()
    query = (data.get("library_last_query") or "").strip()
    page = data.get("library_page", 0)
    await _show_library_list(
        callback.message, machine_library_use_case, query, page=page, use_edit=True
    )
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
