"""Обработчики для редактирования тренажёров."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.application.use_case_interfaces import IMachineManagementUseCase
from src.infrastructure.web.handlers.machine.states import MachineStates
from src.infrastructure.web.handlers.machine.base import safe_edit_text
from src.infrastructure.web.handlers.machine.keyboards import (
    build_muscle_zones_keyboard,
    build_individual_muscles_keyboard,
    KeyboardBuilder,
)

logger = logging.getLogger(__name__)
router = Router()

async def _get_zone_muscle_ids(
    machine_management_use_case: IMachineManagementUseCase,
    zone_ids: list[int],
) -> list[int]:
    if not zone_ids:
        return []
    muscle_ids: set[int] = set()
    for zone_id in zone_ids:
        muscles = await machine_management_use_case.get_muscles_by_zone_id(zone_id)
        muscle_ids.update([m.id for m in muscles])
    return list(muscle_ids)


@router.callback_query(F.data.startswith("edit_machine_menu_"))
async def edit_machine_callback(
    callback: CallbackQuery, 
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик входа в режим редактирования тренажера."""
    user_id = callback.from_user.id
    machine_id = int(callback.data.split('_')[-1])

    try:
        machine = await machine_management_use_case.get_machine_details(user_id, machine_id)
        if not machine:
            logger.warning(f"Пользователь {user_id} попытался редактировать несуществующий или неавторизованный тренажёр {machine_id}.")
            await callback.message.edit_text("Тренажер не найден или у вас нет к нему доступа.")
            await callback.answer()
            return
        
        await state.update_data(editing_machine_id=machine_id)
        zones_str = ", ".join([z.name for z in machine.zones]) if machine.zones else "Не указаны"
        muscles_str = ", ".join([m.name for m in machine.muscles]) if machine.muscles else "Не указаны"
        keyboard = KeyboardBuilder.build_machine_edit_menu_keyboard(machine_id)
        await safe_edit_text(
            callback,
            f"Редактирование тренажера '{machine.name}':\n\n"
            f"Текущие зоны: {zones_str}\n"
            f"Текущие мышцы: {muscles_str}",
            reply_markup=keyboard
        )
        logger.info(f"Пользователь {user_id} вошёл в режим редактирования тренажёра {machine_id}.")

    except Exception as e:
        logger.error(f"Ошибка в edit_machine_callback для пользователя {user_id}, тренажёр {machine_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при входе в режим редактирования.")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("edit_machine_name_"))
async def edit_machine_name_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик начала редактирования названия тренажёра."""
    user_id = callback.from_user.id
    machine_id = int(callback.data.split('_')[-1])
    try:
        await state.update_data(editing_machine_id=machine_id)
        await callback.message.edit_text("Введите новое название тренажера:")
        await state.set_state(MachineStates.waiting_for_edit_name)
        logger.info(f"Пользователь {user_id} редактирует название тренажёра {machine_id}.")
    except Exception as e:
        logger.error(f"Ошибка в edit_machine_name_callback для пользователя {user_id}, тренажёр {machine_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при изменении названия тренажера.")
    finally:
        await callback.answer()


@router.message(MachineStates.waiting_for_edit_name)
async def process_edit_machine_name(
    message: Message, 
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик ввода нового названия тренажёра."""
    user_id = message.from_user.id
    data = await state.get_data()
    machine_id = data.get("editing_machine_id")
    new_name = message.text.strip()

    try:
        if not new_name:
            logger.warning(f"Пользователь {user_id} отправил пустое новое название для тренажёра {machine_id}.")
            await message.answer("Название тренажера не может быть пустым. Попробуйте еще раз.")
            await state.set_state(MachineStates.waiting_for_edit_name)  # Остаться в состоянии
            return

        updated_machine = await machine_management_use_case.update_machine(
            user_id,
            machine_id,
            name=new_name,
            photo_file_id=None,
            zone_ids=None,
            muscle_ids=None,
            is_archived=None,
        )
        if updated_machine:
            logger.info(f"Пользователь {user_id} успешно изменил название тренажёра {machine_id} на '{new_name}'.")
            await message.answer(f"Название тренажера успешно изменено на '{updated_machine.name}'.")
        else:
            logger.warning(f"Пользователь {user_id} не смог изменить название тренажёра {machine_id} на '{new_name}'.")
            await message.answer("Не удалось изменить название тренажера.")
    except ValueError as e:
        logger.warning(f"Ошибка валидации при редактировании названия тренажёра {machine_id} пользователем {user_id}: {e}")
        await message.answer(f"Ошибка: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в process_edit_machine_name для пользователя {user_id}, тренажёр {machine_id}: {e}", exc_info=True)
        await message.answer(f"Произошла непредвиденная ошибка: {e}")
    finally:
        await state.clear()
        # Повторно показать детали тренажёра
        machine = await machine_management_use_case.get_machine_details(user_id, machine_id)
        if machine:
            zones_str = ", ".join([z.name for z in machine.zones]) if machine.zones else "Не указаны"
            muscles_str = ", ".join([m.name for m in machine.muscles]) if machine.muscles else "Не указаны"
            text = f"**{machine.name}**\n" \
                   f"ID: {machine.id}\n" \
                   f"Зоны: {zones_str}\n" \
                   f"Мышцы: {muscles_str}\n" \
                   f"Архивирован: {'Да' if machine.is_archived else 'Нет'}"
            
            keyboard = KeyboardBuilder.build_machine_details_keyboard(machine.id)
            await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("edit_machine_muscles_"))
async def edit_machine_muscles_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик редактирования мышц тренажера - показывает меню выбора."""
    user_id = callback.from_user.id
    machine_id = int(callback.data.split('_')[-1])
    
    logger.info(f"Обработчик edit_machine_muscles_callback вызван для пользователя {user_id}, тренажёр {machine_id}")
    
    try:
        machine = await machine_management_use_case.get_machine_details(user_id, machine_id)
        logger.debug(f"Получена машина для пользователя {user_id}, тренажёр {machine_id}: {machine is not None}")
        if not machine:
            logger.warning(f"Пользователь {user_id} попытался редактировать мышцы несуществующего тренажёра {machine_id}.")
            await callback.message.edit_text("Тренажер не найден или у вас нет к нему доступа.")
            await callback.answer()
            return
        
        current_zone_ids = [z.id for z in machine.zones] if machine.zones else []
        current_muscle_ids = [m.id for m in machine.muscles] if machine.muscles else []
        logger.debug(
            f"Текущие зоны/мышцы тренажёра {machine_id}: {current_zone_ids}/{current_muscle_ids}"
        )
        zone_muscle_ids = await _get_zone_muscle_ids(
            machine_management_use_case, current_zone_ids
        )
        manual_muscle_ids = list(set(current_muscle_ids) - set(zone_muscle_ids))
        await state.update_data(
            editing_machine_id=machine_id,
            selected_zone_ids=current_zone_ids.copy(),
            selected_muscle_ids=current_muscle_ids.copy(),
            manual_muscle_ids=manual_muscle_ids,
        )
        
        # Получаем зоны
        muscle_zones = await machine_management_use_case.get_all_muscle_zones()
        logger.debug(f"Получено зон: {len(muscle_zones) if muscle_zones else 0}")
        
        if not muscle_zones:
            logger.warning(f"В базе данных нет зон для пользователя {user_id}")
            await callback.message.edit_text("В базе данных нет зон.")
            await callback.answer()
            return
        
        # Предлагаем выбрать зоны или отдельные мышцы с визуальной индикацией
        keyboard = await build_muscle_zones_keyboard(
            muscle_zones, current_zone_ids, machine_id, machine_management_use_case, is_creation=False
        )
        
        current_zones = (
            await machine_management_use_case.get_muscle_zones_by_ids(current_zone_ids)
            if current_zone_ids
            else []
        )
        zones_str = ", ".join([z.name for z in current_zones]) if current_zones else "Нет"
        current_muscles = await machine_management_use_case.get_muscles_by_ids(current_muscle_ids) if current_muscle_ids else []
        if current_muscles:
            # Ограничиваем длину списка мышц, чтобы не превысить лимит Telegram (4096 символов)
            muscles_list = [m.name for m in current_muscles]
            muscles_str = ", ".join(muscles_list)
            # Если список слишком длинный, обрезаем его
            max_muscles_in_text = 20  # Показываем максимум 20 мышц в тексте
            if len(muscles_list) > max_muscles_in_text:
                muscles_str = ", ".join(muscles_list[:max_muscles_in_text]) + f" и еще {len(muscles_list) - max_muscles_in_text}..."
        else:
            muscles_str = "Нет"
        
        message_text = (
            f"Редактирование мышц тренажера '{machine.name}':\n\n"
            f"Текущие зоны ({len(current_zone_ids)}):\n{zones_str}\n\n"
            f"Текущие мышцы ({len(current_muscle_ids)}):\n{muscles_str}\n\n"
            "Выберите зоны или отдельные мышцы:"
        )
        
        # Проверяем длину сообщения
        if len(message_text) > 4096:
            logger.warning(f"Сообщение слишком длинное ({len(message_text)} символов) для пользователя {user_id}, тренажёр {machine_id}")
            message_text = (
                f"Редактирование мышц тренажера '{machine.name}':\n\n"
                f"Текущие зоны: {len(current_zone_ids)} шт.\n"
                f"Текущие мышцы: {len(current_muscle_ids)} шт.\n\n"
                "Выберите зоны или отдельные мышцы:"
            )
        
        logger.debug(f"Отправка сообщения для пользователя {user_id}, тренажёр {machine_id}, длина текста: {len(message_text)}")
        
        try:
            await safe_edit_text(
                callback,
                message_text,
                reply_markup=keyboard
            )
            logger.info(f"Сообщение успешно отправлено для пользователя {user_id}, тренажёр {machine_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения для пользователя {user_id}, тренажёр {machine_id}: {e}", exc_info=True)
            raise
        
        await state.set_state(MachineStates.waiting_for_edit_muscle_selection)
        await callback.answer()
        logger.info(f"Обработчик edit_machine_muscles_callback завершён для пользователя {user_id}, тренажёр {machine_id}")
        
    except Exception as e:
        logger.error(f"Ошибка в edit_machine_muscles_callback для пользователя {user_id}, тренажёр {machine_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при редактировании мышц.")
        await callback.answer()


@router.callback_query(F.data.startswith("edit_select_zone_"))
async def edit_select_zone_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик выбора зоны при редактировании."""
    user_id = callback.from_user.id
    zone_id = int(callback.data.split('_')[-1])
    
    try:
        # Получаем данные из FSM
        data = await state.get_data()
        machine_id = data.get("editing_machine_id")
        selected_zone_ids = data.get("selected_zone_ids", [])
        selected_zone_ids = data.get("selected_zone_ids", [])
        manual_muscle_ids = data.get("manual_muscle_ids", [])
        
        if not machine_id:
            await callback.message.edit_text("Ошибка: ID тренажера не найден.")
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

        zone_muscle_ids = await _get_zone_muscle_ids(
            machine_management_use_case, selected_zone_ids
        )
        selected_muscle_ids = list(set(zone_muscle_ids) | set(manual_muscle_ids))
        await state.update_data(
            selected_zone_ids=selected_zone_ids,
            selected_muscle_ids=selected_muscle_ids,
            manual_muscle_ids=manual_muscle_ids,
        )
        await callback.answer(action_text)
        
        # Обновляем сообщение с актуальным состоянием
        machine = await machine_management_use_case.get_machine_details(user_id, machine_id)
        if not machine:
            await callback.message.edit_text("Ошибка: тренажер не найден.")
            return
        
        # Получаем зоны для меню
        muscle_zones = await machine_management_use_case.get_all_muscle_zones()
        if not muscle_zones:
            await callback.message.edit_text("В базе данных нет зон.")
            return
        
        # Создаем клавиатуру с визуальной индикацией
        keyboard = await build_muscle_zones_keyboard(
            muscle_zones, selected_zone_ids, machine_id, machine_management_use_case, is_creation=False
        )
        
        # Формируем текст с обновленным списком мышц
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
            f"Редактирование мышц тренажера '{machine.name}':\n\n"
            f"Текущие зоны ({len(selected_zone_ids)}):\n{zones_str}\n\n"
            f"Текущие мышцы ({len(selected_muscle_ids)}):\n{muscles_str}\n\n"
            "Выберите зоны или отдельные мышцы:"
        )
        
        if len(message_text) > 4096:
            message_text = (
                f"Редактирование мышц тренажера '{machine.name}':\n\n"
                f"Текущие зоны: {len(selected_zone_ids)} шт.\n"
                f"Текущие мышцы: {len(selected_muscle_ids)} шт.\n\n"
                "Выберите зоны или отдельные мышцы:"
            )
        
        await safe_edit_text(callback, message_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(
            f"Ошибка в edit_select_zone_callback для пользователя {user_id}, зона {zone_id}: {e}",
            exc_info=True,
        )
        await callback.message.answer("Произошла ошибка при выборе зоны.")
        await callback.answer()


@router.callback_query(F.data == "edit_select_individual_muscles")
async def edit_select_individual_muscles_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик выбора отдельных мышц при редактировании - показывает список всех мышц."""
    user_id = callback.from_user.id
    
    try:
        data = await state.get_data()
        machine_id = data.get("editing_machine_id")
        selected_zone_ids = data.get("selected_zone_ids", [])
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        if not machine_id:
            await callback.message.edit_text("Ошибка: ID тренажера не найден.")
            await callback.answer()
            await state.clear()
            return
        
        machine = await machine_management_use_case.get_machine_details(user_id, machine_id)
        if not machine:
            await callback.message.edit_text("Тренажер не найден.")
            await callback.answer()
            return
        
        # Получаем все мышцы
        all_muscles = await machine_management_use_case.get_all_muscles()
        
        if not all_muscles:
            await callback.answer("В базе данных нет мышц.", show_alert=True)
            return
        
        keyboard = await build_individual_muscles_keyboard(
            all_muscles, selected_muscle_ids, machine_id, is_creation=False
        )
        
        selected_zones = (
            await machine_management_use_case.get_muscle_zones_by_ids(selected_zone_ids)
            if selected_zone_ids
            else []
        )
        selected_muscles = await machine_management_use_case.get_muscles_by_ids(selected_muscle_ids) if selected_muscle_ids else []
        zones_str = ", ".join([z.name for z in selected_zones]) if selected_zones else "Нет"
        muscles_str = ", ".join([m.name for m in selected_muscles]) if selected_muscles else "Нет"
        
        await safe_edit_text(
            callback,
            f"Редактирование мышц тренажера '{machine.name}':\n\n"
            f"Выбранные зоны ({len(selected_zone_ids)}):\n{zones_str}\n\n"
            f"Выбранные мышцы ({len(selected_muscle_ids)}):\n{muscles_str}\n\n"
            "Нажмите на мышцу, чтобы добавить/удалить её:",
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в edit_select_individual_muscles_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при загрузке списка мышц.")
        await callback.answer()


@router.callback_query(F.data.startswith("toggle_edit_muscle_"))
async def toggle_edit_muscle_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик переключения выбора мышцы при редактировании."""
    user_id = callback.from_user.id
    muscle_id = int(callback.data.split('_')[-1])
    
    try:
        data = await state.get_data()
        machine_id = data.get("editing_machine_id")
        if not machine_id:
            await callback.answer("Ошибка: ID тренажера не найден.", show_alert=True)
            return
        
        selected_zone_ids = data.get("selected_zone_ids", [])
        manual_muscle_ids = data.get("manual_muscle_ids", [])
        
        if muscle_id in manual_muscle_ids:
            manual_muscle_ids.remove(muscle_id)
            action = "удалена"
        else:
            manual_muscle_ids.append(muscle_id)
            action = "добавлена"
        
        zone_muscle_ids = await _get_zone_muscle_ids(
            machine_management_use_case, selected_zone_ids
        )
        selected_muscle_ids = list(set(zone_muscle_ids) | set(manual_muscle_ids))
        await state.update_data(
            selected_muscle_ids=selected_muscle_ids,
            manual_muscle_ids=manual_muscle_ids,
        )
        
        muscle = await machine_management_use_case.get_muscle_by_id(muscle_id)
        muscle_name = muscle.name if muscle else f"Мышца {muscle_id}"
        
        await callback.answer(f"Мышца '{muscle_name}' {action}")
        
        # Обновляем сообщение - вызываем edit_select_individual_muscles_callback заново
        await edit_select_individual_muscles_callback(callback, state, machine_management_use_case)
        
    except Exception as e:
        logger.error(f"Ошибка в toggle_edit_muscle_callback для пользователя {user_id}, мышца {muscle_id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при выборе мышцы.")


@router.callback_query(F.data == "save_machine_muscles")
async def save_machine_muscles_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик сохранения изменений мышц тренажера."""
    user_id = callback.from_user.id
    
    try:
        data = await state.get_data()
        machine_id = data.get("editing_machine_id")
        selected_zone_ids = data.get("selected_zone_ids", [])
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        if not machine_id:
            await callback.message.edit_text("Ошибка: ID тренажера не найден.")
            await callback.answer()
            await state.clear()
            return
        
        # Обновляем мышцы тренажера
        updated_machine = await machine_management_use_case.update_machine(
            user_id, machine_id, name=None, photo_file_id=None,
            zone_ids=selected_zone_ids, muscle_ids=selected_muscle_ids, is_archived=None
        )
        
        if not updated_machine:
            await callback.message.edit_text("Не удалось обновить мышцы тренажера.")
            await callback.answer()
            await state.clear()
            return
        
        logger.info(
            f"Пользователь {user_id} обновил зоны/мышцы тренажёра {machine_id}: {selected_zone_ids}/{selected_muscle_ids}"
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
            f"✅ Мышцы тренажера '{updated_machine.name}' успешно обновлены!\n\n"
            f"Зоны: {zones_str}\n"
            f"Мышцы: {muscles_str}"
        )
        await callback.answer()
        await state.clear()
        
        # Показываем детали тренажера
        machine = await machine_management_use_case.get_machine_details(user_id, machine_id)
        if machine:
            zones_str = ", ".join([z.name for z in machine.zones]) if machine.zones else "Не указаны"
            muscles_str = ", ".join([m.name for m in machine.muscles]) if machine.muscles else "Не указаны"
            text = f"**{machine.name}**\n" \
                   f"ID: {machine.id}\n" \
                   f"Зоны: {zones_str}\n" \
                   f"Мышцы: {muscles_str}\n" \
                   f"Архивирован: {'Да' if machine.is_archived else 'Нет'}"
            
            keyboard = KeyboardBuilder.build_machine_details_keyboard(machine.id)
            await callback.message.answer(text, reply_markup=keyboard)
        
    except ValueError as e:
        logger.warning(f"Ошибка валидации при сохранении мышц тренажёра для пользователя {user_id}: {e}")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в save_machine_muscles_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при сохранении мышц.")
        await callback.answer()
        await state.clear()


@router.callback_query(F.data == "zone_header")
async def zone_header_callback(
    callback: CallbackQuery,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик неактивной кнопки заголовка группы - просто отвечает пустым ответом."""
    await callback.answer()
