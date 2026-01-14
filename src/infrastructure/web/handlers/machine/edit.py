"""Обработчики для редактирования тренажёров."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.application.use_case_interfaces import IMachineManagementUseCase
from src.infrastructure.web.handlers.machine.states import MachineStates
from src.infrastructure.web.handlers.machine.base import safe_edit_text
from src.infrastructure.web.handlers.machine.keyboards import (
    build_muscle_groups_keyboard,
    build_individual_muscles_keyboard,
    KeyboardBuilder,
)

logger = logging.getLogger(__name__)
router = Router()


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
        muscles_str = ", ".join([m.name for m in machine.muscles]) if machine.muscles else "Не указаны"
        keyboard = KeyboardBuilder.build_machine_edit_menu_keyboard(machine_id)
        await safe_edit_text(
            callback,
            f"Редактирование тренажера '{machine.name}':\n\n"
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

        updated_machine = await machine_management_use_case.update_machine(user_id, machine_id, name=new_name)
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
            muscles_str = ", ".join([m.name for m in machine.muscles]) if machine.muscles else "Не указаны"
            text = f"**{machine.name}**\n" \
                   f"ID: {machine.id}\n" \
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
        
        current_muscle_ids = [m.id for m in machine.muscles] if machine.muscles else []
        logger.debug(f"Текущие мышцы тренажёра {machine_id}: {current_muscle_ids}")
        await state.update_data(
            editing_machine_id=machine_id,
            selected_muscle_ids=current_muscle_ids.copy()
        )
        
        # Получаем группы мышц
        muscle_groups = await machine_management_use_case.get_all_muscle_groups()
        logger.debug(f"Получено групп мышц: {len(muscle_groups) if muscle_groups else 0}")
        
        if not muscle_groups:
            logger.warning(f"В базе данных нет групп мышц для пользователя {user_id}")
            await callback.message.edit_text("В базе данных нет групп мышц.")
            await callback.answer()
            return
        
        # Предлагаем выбрать группы мышц или отдельные мышцы с визуальной индикацией
        keyboard = await build_muscle_groups_keyboard(
            muscle_groups, current_muscle_ids, machine_id, machine_management_use_case, is_creation=False
        )
        
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
            f"Текущие мышцы ({len(current_muscle_ids)}):\n{muscles_str}\n\n"
            "Выберите группы мышц или отдельные мышцы:"
        )
        
        # Проверяем длину сообщения
        if len(message_text) > 4096:
            logger.warning(f"Сообщение слишком длинное ({len(message_text)} символов) для пользователя {user_id}, тренажёр {machine_id}")
            message_text = (
                f"Редактирование мышц тренажера '{machine.name}':\n\n"
                f"Текущие мышцы: {len(current_muscle_ids)} шт.\n\n"
                "Выберите группы мышц или отдельные мышцы:"
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


@router.callback_query(F.data.startswith("edit_select_group_"))
async def edit_select_group_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик выбора группы мышц при редактировании - переключает все мышцы группы (добавляет/удаляет)."""
    user_id = callback.from_user.id
    group_id = int(callback.data.split('_')[-1])
    
    try:
        # Получаем мышцы группы
        muscles = await machine_management_use_case.get_muscles_by_group_id(group_id)
        
        if not muscles:
            await callback.answer("В этой группе нет мышц.", show_alert=True)
            return
        
        # Получаем данные из FSM
        data = await state.get_data()
        machine_id = data.get("editing_machine_id")
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        if not machine_id:
            await callback.message.edit_text("Ошибка: ID тренажера не найден.")
            await callback.answer()
            await state.clear()
            return
        
        # Получаем группу для отображения
        group = await machine_management_use_case.get_muscle_group_by_id(group_id)
        group_name = group.name if group else f"Группа {group_id}"
        
        # Проверяем, все ли мышцы группы уже выбраны
        group_muscle_ids = [m.id for m in muscles]
        all_selected = all(mid in selected_muscle_ids for mid in group_muscle_ids)
        
        if all_selected:
            # Удаляем все мышцы группы
            selected_muscle_ids = [mid for mid in selected_muscle_ids if mid not in group_muscle_ids]
            action_text = f"Удалены мышцы из группы '{group_name}'"
        else:
            # Добавляем все мышцы группы (только те, которых еще нет)
            new_muscle_ids = [mid for mid in group_muscle_ids if mid not in selected_muscle_ids]
            selected_muscle_ids.extend(new_muscle_ids)
            action_text = f"Добавлены мышцы из группы '{group_name}'"
        
        await state.update_data(selected_muscle_ids=selected_muscle_ids)
        await callback.answer(action_text)
        
        # Обновляем сообщение с актуальным состоянием
        machine = await machine_management_use_case.get_machine_details(user_id, machine_id)
        if not machine:
            await callback.message.edit_text("Ошибка: тренажер не найден.")
            return
        
        # Получаем группы мышц для меню
        muscle_groups = await machine_management_use_case.get_all_muscle_groups()
        if not muscle_groups:
            await callback.message.edit_text("В базе данных нет групп мышц.")
            return
        
        # Создаем клавиатуру с визуальной индикацией
        keyboard = await build_muscle_groups_keyboard(
            muscle_groups, selected_muscle_ids, machine_id, machine_management_use_case, is_creation=False
        )
        
        # Формируем текст с обновленным списком мышц
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
            f"Текущие мышцы ({len(selected_muscle_ids)}):\n{muscles_str}\n\n"
            "Выберите группы мышц или отдельные мышцы:"
        )
        
        if len(message_text) > 4096:
            message_text = (
                f"Редактирование мышц тренажера '{machine.name}':\n\n"
                f"Текущие мышцы: {len(selected_muscle_ids)} шт.\n\n"
                "Выберите группы мышц или отдельные мышцы:"
            )
        
        await safe_edit_text(callback, message_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка в edit_select_group_callback для пользователя {user_id}, группа {group_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при выборе группы мышц.")
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
        
        # Получаем все мышцы, сгруппированные по группам
        all_muscles = await machine_management_use_case.get_all_muscles()
        
        if not all_muscles:
            await callback.answer("В базе данных нет мышц.", show_alert=True)
            return
        
        keyboard = await build_individual_muscles_keyboard(
            all_muscles, selected_muscle_ids, machine_id, is_creation=False
        )
        
        selected_muscles = await machine_management_use_case.get_muscles_by_ids(selected_muscle_ids) if selected_muscle_ids else []
        muscles_str = ", ".join([m.name for m in selected_muscles]) if selected_muscles else "Нет"
        
        await safe_edit_text(
            callback,
            f"Редактирование мышц тренажера '{machine.name}':\n\n"
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
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        if not machine_id:
            await callback.message.edit_text("Ошибка: ID тренажера не найден.")
            await callback.answer()
            await state.clear()
            return
        
        # Обновляем мышцы тренажера
        updated_machine = await machine_management_use_case.update_machine(
            user_id, machine_id, name=None, photo_file_id=None,
            muscle_ids=selected_muscle_ids, is_archived=None
        )
        
        if not updated_machine:
            await callback.message.edit_text("Не удалось обновить мышцы тренажера.")
            await callback.answer()
            await state.clear()
            return
        
        logger.info(
            f"Пользователь {user_id} обновил мышцы тренажёра {machine_id}: {selected_muscle_ids}"
        )
        
        muscles_str = "Не указаны"
        if selected_muscle_ids:
            selected_muscles = await machine_management_use_case.get_muscles_by_ids(selected_muscle_ids)
            muscles_str = ", ".join([m.name for m in selected_muscles])
        
        await callback.message.edit_text(
            f"✅ Мышцы тренажера '{updated_machine.name}' успешно обновлены!\n\n"
            f"Мышцы: {muscles_str}"
        )
        await callback.answer()
        await state.clear()
        
        # Показываем детали тренажера
        machine = await machine_management_use_case.get_machine_details(user_id, machine_id)
        if machine:
            muscles_str = ", ".join([m.name for m in machine.muscles]) if machine.muscles else "Не указаны"
            text = f"**{machine.name}**\n" \
                   f"ID: {machine.id}\n" \
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


@router.callback_query(F.data == "muscle_group_header")
async def muscle_group_header_callback(
    callback: CallbackQuery,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик неактивной кнопки заголовка группы - просто отвечает пустым ответом."""
    await callback.answer()
