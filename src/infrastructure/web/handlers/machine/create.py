"""Обработчики для создания тренажёров."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from pydantic import ValidationError

from src.application.use_case_interfaces import IMachineManagementUseCase
from src.application.dto import MachineInputDTO
from src.infrastructure.web.handlers.machine.states import MachineStates
from src.infrastructure.web.handlers.machine.base import safe_edit_text
from src.infrastructure.web.handlers.machine.keyboards import (
    build_muscle_zones_keyboard,
    build_individual_muscles_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "add_machine")
async def add_machine_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик начала процесса добавления тренажёра."""
    try:
        logger.info(f"Пользователь {callback.from_user.id} инициировал процесс добавления тренажёра.")
        await callback.message.edit_text("Введите название нового тренажера:")
        await state.set_state(MachineStates.waiting_for_machine_name)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в add_machine_callback для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при начале добавления тренажера.")
        await callback.answer()


@router.message(MachineStates.waiting_for_machine_name)
async def process_machine_name(
    message: Message,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик ввода названия тренажёра."""
    user_id = message.from_user.id
    
    try:
        # Валидация через Pydantic DTO
        try:
            machine_input = MachineInputDTO(name=message.text)
        except ValidationError as e:
            error_messages = "; ".join([err["msg"] for err in e.errors()])
            logger.warning(
                f"Пользователь {user_id} отправил невалидное название тренажёра.",
                extra={"errors": error_messages},
            )
            await message.answer(f"Ошибка валидации: {error_messages}. Попробуйте еще раз.")
            return

        machine_exists = await machine_management_use_case.check_machine_name_exists(user_id, machine_input.name)
        if machine_exists:
            logger.warning(f"Пользователь {user_id} попытался добавить дублирующееся название тренажёра: {machine_input.name}")
            await message.answer(f"Тренажер с названием '{machine_input.name}' уже существует. Попробуйте другое название.")
            return

        # Сохраняем название в FSM и переходим к выбору мышц
        await state.update_data(
            machine_name=machine_input.name,
            selected_zone_ids=[],
            selected_muscle_ids=[],
        )
        
        # Получаем зоны
        muscle_zones = await machine_management_use_case.get_all_muscle_zones()
        
        if not muscle_zones:
            logger.warning("В базе данных нет зон. Создаю тренажер без зон/мышц.")
            new_machine = await machine_management_use_case.add_machine(
                user_id, machine_input.name, None, [], []
            )
            logger.info(
                "Пользователь %s успешно добавил тренажёр %s (%s).",
                user_id,
                new_machine.id,
                new_machine.name,
            )
            await message.answer(
                f"Тренажер '{new_machine.name}' успешно добавлен! (В базе данных пока нет зон)"
            )
            await state.clear()
            return
        
        # Предлагаем выбрать зоны или отдельные мышцы
        keyboard = await build_muscle_zones_keyboard(
            muscle_zones, [], None, machine_management_use_case, is_creation=True
        )
        
        await message.answer(
            f"Тренажер '{machine_input.name}' сохранен.\n\n"
            "Выберите зоны или отдельные мышцы для этого тренажера:",
            reply_markup=keyboard
        )
        await state.set_state(MachineStates.waiting_for_muscle_selection)
        logger.info(f"Пользователь {user_id} ввел название тренажёра '{machine_input.name}', переходит к выбору мышц.")

    except ValueError as e:
        logger.warning(f"Ошибка валидации при добавлении тренажёра пользователем {user_id}: {e}")
        await message.answer(f"Ошибка: {e}")
        await state.clear()
    except Exception as e:
        logger.error(f"Неожиданная ошибка в process_machine_name для пользователя {user_id}: {e}", exc_info=True)
        await message.answer(f"Произошла непредвиденная ошибка: {e}")
        await state.clear()


@router.callback_query(F.data == "skip_muscle_selection")
async def skip_muscle_selection_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик пропуска выбора мышц - создает тренажер без мышц."""
    user_id = callback.from_user.id
    try:
        data = await state.get_data()
        machine_name = data.get("machine_name")
        
        if not machine_name:
            await callback.message.edit_text("Ошибка: название тренажера не найдено.")
            await callback.answer()
            await state.clear()
            return
        
        new_machine = await machine_management_use_case.add_machine(
            user_id, machine_name, None, [], []
        )
        logger.info(f"Пользователь {user_id} успешно добавил тренажёр {new_machine.id} ({new_machine.name}) без мышц.")
        await callback.message.edit_text(f"Тренажер '{new_machine.name}' успешно добавлен!")
        await callback.answer()
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в skip_muscle_selection_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при создании тренажера.")
        await callback.answer()
        await state.clear()


@router.callback_query(F.data.startswith("select_zone_"))
async def select_zone_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик выбора зоны при создании."""
    user_id = callback.from_user.id
    zone_id = int(callback.data.split('_')[-1])
    
    try:
        # Получаем данные из FSM
        data = await state.get_data()
        machine_name = data.get("machine_name")
        selected_zone_ids = data.get("selected_zone_ids", [])
        selected_zone_ids = data.get("selected_zone_ids", [])
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        if not machine_name:
            await callback.message.edit_text("Ошибка: название тренажера не найдено.")
            await callback.answer()
            await state.clear()
            return
        
        zone = await machine_management_use_case.get_muscle_zone_by_id(zone_id)
        zone_name = zone.name if zone else f"Зона {zone_id}"

        if zone_id in selected_zone_ids:
            selected_zone_ids.remove(zone_id)
            action_text = f"Зона '{zone_name}' удалена"
        else:
            selected_zone_ids.append(zone_id)
            action_text = f"Зона '{zone_name}' добавлена"

        await state.update_data(
            selected_zone_ids=selected_zone_ids,
            selected_muscle_ids=selected_muscle_ids,
        )
        await callback.answer(action_text)
        
        # Получаем зоны для меню
        muscle_zones = await machine_management_use_case.get_all_muscle_zones()
        if not muscle_zones:
            await callback.message.edit_text("В базе данных нет зон.")
            return
        
        # Создаем клавиатуру с визуальной индикацией
        keyboard = await build_muscle_zones_keyboard(
            muscle_zones, selected_zone_ids, None, machine_management_use_case, is_creation=True
        )
        
        # Формируем текст с обновленным списком зон и мышц
        selected_zones = (
            await machine_management_use_case.get_muscle_zones_by_ids(selected_zone_ids)
            if selected_zone_ids
            else []
        )
        zones_str = ", ".join([z.name for z in selected_zones]) if selected_zones else "Нет"
        selected_muscles = await machine_management_use_case.get_muscles_by_ids(selected_muscle_ids) if selected_muscle_ids else []
        if selected_muscles:
            muscles_list = [m.name for m in selected_muscles]
            muscles_str = ", ".join(muscles_list)
            max_muscles_in_text = 20
            if len(muscles_list) > max_muscles_in_text:
                muscles_str = ", ".join(muscles_list[:max_muscles_in_text]) + f" и еще {len(muscles_list) - max_muscles_in_text}..."
        else:
            muscles_str = "Нет"
        
        message_text = (
            f"Тренажер: {machine_name}\n\n"
            f"Выбранные зоны ({len(selected_zone_ids)}):\n{zones_str}\n\n"
            f"Выбранные мышцы ({len(selected_muscle_ids)}):\n{muscles_str}\n\n"
            "Выберите зоны или отдельные мышцы:"
        )
        
        if len(message_text) > 4096:
            message_text = (
                f"Тренажер: {machine_name}\n\n"
                f"Выбранные зоны: {len(selected_zone_ids)} шт.\n"
                f"Выбранные мышцы: {len(selected_muscle_ids)} шт.\n\n"
                "Выберите зоны или отдельные мышцы:"
            )
        
        await safe_edit_text(callback, message_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(
            f"Ошибка в select_zone_callback для пользователя {user_id}, зона {zone_id}: {e}",
            exc_info=True,
        )
        await callback.message.answer("Произошла ошибка при выборе зоны.")
        await callback.answer()


@router.callback_query(F.data == "select_individual_muscles")
async def select_individual_muscles_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик выбора отдельных мышц - показывает список всех мышц."""
    user_id = callback.from_user.id
    
    try:
        # Получаем все мышцы
        all_muscles = await machine_management_use_case.get_all_muscles()
        
        if not all_muscles:
            await callback.answer("В базе данных нет мышц.", show_alert=True)
            return
        
        # Получаем данные из FSM один раз
        data = await state.get_data()
        machine_name = data.get("machine_name", "Новый тренажер")
        selected_zone_ids = data.get("selected_zone_ids", [])
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        keyboard = await build_individual_muscles_keyboard(
            all_muscles, selected_muscle_ids, None, is_creation=True
        )
        
        selected_zones = (
            await machine_management_use_case.get_muscle_zones_by_ids(selected_zone_ids)
            if selected_zone_ids
            else []
        )
        selected_muscles = await machine_management_use_case.get_muscles_by_ids(selected_muscle_ids) if selected_muscle_ids else []
        zones_str = ", ".join([z.name for z in selected_zones]) if selected_zones else "Нет"
        selected_names = ", ".join([m.name for m in selected_muscles]) if selected_muscles else "Нет"
        
        await callback.message.edit_text(
            f"Тренажер: {machine_name}\n\n"
            f"Выбранные зоны ({len(selected_zone_ids)}):\n{zones_str}\n\n"
            f"Выбранные мышцы ({len(selected_muscle_ids)}):\n{selected_names}\n\n"
            "Нажмите на мышцу, чтобы добавить/удалить её:",
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в select_individual_muscles_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при загрузке списка мышц.")
        await callback.answer()


@router.callback_query(F.data.startswith("toggle_muscle_"))
async def toggle_muscle_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик переключения выбора отдельной мышцы."""
    user_id = callback.from_user.id
    muscle_id = int(callback.data.split('_')[-1])
    
    try:
        data = await state.get_data()
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        if muscle_id in selected_muscle_ids:
            selected_muscle_ids.remove(muscle_id)
            action = "удалена"
        else:
            selected_muscle_ids.append(muscle_id)
            action = "добавлена"
        
        await state.update_data(selected_muscle_ids=selected_muscle_ids)
        
        muscle = await machine_management_use_case.get_muscle_by_id(muscle_id)
        muscle_name = muscle.name if muscle else f"Мышца {muscle_id}"
        
        await callback.answer(f"Мышца '{muscle_name}' {action}")
        
        # Обновляем сообщение с текущим состоянием
        await select_individual_muscles_callback(callback, state, machine_management_use_case)
        
    except Exception as e:
        logger.error(f"Ошибка в toggle_muscle_callback для пользователя {user_id}, мышца {muscle_id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при выборе мышцы.")


@router.callback_query(F.data == "add_more_muscles")
async def add_more_muscles_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик для возврата к выбору мышц."""
    user_id = callback.from_user.id
    
    try:
        # Получаем зоны
        muscle_zones = await machine_management_use_case.get_all_muscle_zones()
        
        if not muscle_zones:
            await callback.answer("В базе данных нет зон.", show_alert=True)
            return
        
        data = await state.get_data()
        machine_name = data.get("machine_name", "Новый тренажер")
        selected_zone_ids = data.get("selected_zone_ids", [])
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        # Создаем клавиатуру с визуальной индикацией
        keyboard = await build_muscle_zones_keyboard(
            muscle_zones, selected_zone_ids, None, machine_management_use_case, is_creation=True
        )
        
        selected_zones = (
            await machine_management_use_case.get_muscle_zones_by_ids(selected_zone_ids)
            if selected_zone_ids
            else []
        )
        selected_muscles = await machine_management_use_case.get_muscles_by_ids(selected_muscle_ids) if selected_muscle_ids else []
        zones_str = ", ".join([z.name for z in selected_zones]) if selected_zones else "Нет"
        if selected_muscles:
            muscles_list = [m.name for m in selected_muscles]
            muscles_str = ", ".join(muscles_list)
            max_muscles_in_text = 20
            if len(muscles_list) > max_muscles_in_text:
                muscles_str = ", ".join(muscles_list[:max_muscles_in_text]) + f" и еще {len(muscles_list) - max_muscles_in_text}..."
        else:
            muscles_str = "Нет"
        
        message_text = (
            f"Тренажер: {machine_name}\n\n"
            f"Выбранные зоны ({len(selected_zone_ids)}):\n{zones_str}\n\n"
            f"Выбранные мышцы ({len(selected_muscle_ids)}):\n{muscles_str}\n\n"
            "Выберите зоны или отдельные мышцы:"
        )
        
        if len(message_text) > 4096:
            message_text = (
                f"Тренажер: {machine_name}\n\n"
                f"Выбранные зоны: {len(selected_zone_ids)} шт.\n"
                f"Выбранные мышцы: {len(selected_muscle_ids)} шт.\n\n"
                "Выберите зоны или отдельные мышцы:"
            )
        
        await safe_edit_text(callback, message_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в add_more_muscles_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка.")
        await callback.answer()


@router.callback_query(F.data == "finish_machine_creation")
async def finish_machine_creation_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик завершения создания тренажера."""
    user_id = callback.from_user.id
    
    try:
        data = await state.get_data()
        machine_name = data.get("machine_name")
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        if not machine_name:
            await callback.message.edit_text("Ошибка: название тренажера не найдено.")
            await callback.answer()
            await state.clear()
            return
        
        # Создаем тренажер с выбранными мышцами
        new_machine = await machine_management_use_case.add_machine(
            user_id, machine_name, None, selected_zone_ids, selected_muscle_ids
        )
        
        logger.info(
            f"Пользователь {user_id} успешно добавил тренажёр {new_machine.id} "
            f"({new_machine.name}) с {len(selected_muscle_ids)} мышцами."
        )
        
        zones_str = "Не указаны"
        if selected_zone_ids:
            selected_zones = await machine_management_use_case.get_muscle_zones_by_ids(selected_zone_ids)
            zones_str = ", ".join([z.name for z in selected_zones])

        muscles_str = "Не указаны"
        if selected_muscle_ids:
            selected_muscles = await machine_management_use_case.get_muscles_by_ids(selected_muscle_ids)
            muscles_str = ", ".join([m.name for m in selected_muscles])
        
        await callback.message.edit_text(
            f"✅ Тренажер '{new_machine.name}' успешно добавлен!\n\n"
            f"Зоны: {zones_str}\n"
            f"Мышцы: {muscles_str}"
        )
        await callback.answer()
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в finish_machine_creation_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при создании тренажера.")
        await callback.answer()
        await state.clear()
