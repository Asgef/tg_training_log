"""Handler для управления тренажёрами."""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from pydantic import ValidationError

from src.application.use_case_interfaces import IMachineManagementUseCase
from src.application.dto import MachineInputDTO, MachineUpdateInputDTO

logger = logging.getLogger(__name__)

router = Router()


async def safe_edit_text(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Безопасное редактирование текста сообщения с обработкой ошибки 'message is not modified'"""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        logger.debug(f"Сообщение успешно отредактировано для пользователя {callback.from_user.id}")
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "message is not modified" in error_msg:
            logger.debug(f"Сообщение не изменилось для пользователя {callback.from_user.id}")
        else:
            logger.error(f"TelegramBadRequest при редактировании сообщения для пользователя {callback.from_user.id}: {e}")
            raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при редактировании сообщения для пользователя {callback.from_user.id}: {e}", exc_info=True)
        raise

class MachineStates(StatesGroup):
    waiting_for_machine_name = State()
    waiting_for_machine_photo = State()
    waiting_for_muscle_selection = State()
    waiting_for_edit_name = State()
    waiting_for_edit_photo = State()
    waiting_for_edit_muscle_selection = State()

@router.message(Command("machines"))
async def cmd_machines(
    message: Message,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    try:
        logger.info(f"Пользователь {message.from_user.id} использовал команду /machines.")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить тренажер", callback_data="add_machine")],
            [InlineKeyboardButton(text="Мои тренажеры", callback_data="list_machines")]
        ])
        await message.answer("Управление тренажерами:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в cmd_machines для пользователя {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке команды /machines.")


@router.callback_query(F.data == "add_machine")
async def add_machine_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
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
    user_id = message.from_user.id
    
    try:
        # Валидация через Pydantic DTO
        try:
            machine_input = MachineInputDTO(name=message.text)
        except ValidationError as e:
            error_messages = "; ".join([err["msg"] for err in e.errors()])
            logger.warning(
                f"Пользователь {user_id} отправил невалидное название тренажёра.",
                errors=error_messages,
            )
            await message.answer(f"Ошибка валидации: {error_messages}. Попробуйте еще раз.")
            return

        machine_exists = await machine_management_use_case.check_machine_name_exists(user_id, machine_input.name)
        if machine_exists:
            logger.warning(f"Пользователь {user_id} попытался добавить дублирующееся название тренажёра: {machine_input.name}")
            await message.answer(f"Тренажер с названием '{machine_input.name}' уже существует. Попробуйте другое название.")
            return

        # Сохраняем название в FSM и переходим к выбору мышц
        await state.update_data(machine_name=machine_input.name, selected_muscle_ids=[])
        
        # Получаем группы мышц
        muscle_groups = await machine_management_use_case.get_all_muscle_groups()
        
        if not muscle_groups:
            logger.warning(f"В базе данных нет групп мышц. Создаю тренажер без мышц.")
            new_machine = await machine_management_use_case.add_machine(user_id, machine_input.name, None, [])
            logger.info(f"Пользователь {user_id} успешно добавил тренажёр {new_machine.id} ({new_machine.name}).")
            await message.answer(f"Тренажер '{new_machine.name}' успешно добавлен! (В базе данных пока нет групп мышц)")
            await state.clear()
            return
        
        # Предлагаем выбрать группы мышц или отдельные мышцы с визуальной индикацией
        keyboard = await _build_muscle_groups_keyboard_for_creation(muscle_groups, [], machine_management_use_case)
        
        await message.answer(
            f"Тренажер '{machine_input.name}' сохранен.\n\n"
            "Выберите группы мышц или отдельные мышцы для этого тренажера:",
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


@router.callback_query(F.data == "list_machines")
async def list_machines_callback(
    callback: CallbackQuery,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    user_id = callback.from_user.id
    try:
        machines = await machine_management_use_case.get_user_machines(user_id)

        if not machines:
            logger.info(f"Пользователь {user_id} запросил список тренажёров, ничего не найдено.")
            await callback.message.edit_text("У вас пока нет добавленных тренажеров.")
            await callback.answer()
            return

        text = "Ваши тренажеры:\n"
        keyboard_buttons = []
        for machine in machines:
            text += f"ID: {machine.id}, Название: {machine.name}\n"
            keyboard_buttons.append([InlineKeyboardButton(text=machine.name, callback_data=f"view_machine_{machine.id}")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
        logger.info(f"Пользователь {user_id} просмотрел список из {len(machines)} тренажёров.")

    except Exception as e:
        logger.error(f"Ошибка в list_machines_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при получении списка тренажеров.")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("view_machine_"))
async def view_machine_details_callback(
    callback: CallbackQuery,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    user_id = callback.from_user.id
    machine_id = int(callback.data.split('_')[-1])

    try:
        machine = await machine_management_use_case.get_machine_details(user_id, machine_id)

        if not machine:
            logger.warning(f"Пользователь {user_id} попытался просмотреть несуществующий или неавторизованный тренажёр {machine_id}.")
            await callback.message.edit_text("Тренажер не найден или у вас нет к нему доступа.")
            await callback.answer()
            return

        muscles_str = ", ".join([m.name for m in machine.muscles]) if machine.muscles else "Не указаны"
        text = f"**{machine.name}**\n" \
               f"ID: {machine.id}\n" \
               f"Мышцы: {muscles_str}\n" \
               f"Архивирован: {'Да' if machine.is_archived else 'Нет'}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_machine_menu_{machine.id}")],
            [InlineKeyboardButton(text="Архивировать", callback_data=f"archive_machine_{machine.id}")],
            [InlineKeyboardButton(text="Назад к списку", callback_data="list_machines")]
        ])
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


async def _build_muscle_groups_keyboard(
    muscle_groups, 
    selected_muscle_ids: list[int], 
    machine_id: int,
    machine_management_use_case: IMachineManagementUseCase
) -> InlineKeyboardMarkup:
    """Вспомогательная функция для построения клавиатуры с группами мышц и визуальной индикацией (для редактирования)"""
    keyboard_buttons = []
    
    for group in muscle_groups:
        # Получаем мышцы группы для проверки статуса
        group_muscles = await machine_management_use_case.get_muscles_by_group_id(group.id)
        group_muscle_ids = [m.id for m in group_muscles] if group_muscles else []
        
        # Проверяем, все ли мышцы группы выбраны
        all_selected = all(mid in selected_muscle_ids for mid in group_muscle_ids) if group_muscle_ids else False
        some_selected = any(mid in selected_muscle_ids for mid in group_muscle_ids) if group_muscle_ids else False
        
        # Выбираем эмодзи в зависимости от статуса
        if all_selected:
            emoji = "✅"
        elif some_selected:
            emoji = "🟡"
        else:
            emoji = "📦"
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {group.name}",
                callback_data=f"edit_select_group_{group.id}"
            )
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(
            text="🔍 Выбрать отдельные мышцы",
            callback_data="edit_select_individual_muscles"
        )
    ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="✅ Сохранить изменения", callback_data="save_machine_muscles")
    ])
    keyboard_buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_machine_{machine_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


async def _build_muscle_groups_keyboard_for_creation(
    muscle_groups, 
    selected_muscle_ids: list[int],
    machine_management_use_case: IMachineManagementUseCase
) -> InlineKeyboardMarkup:
    """Вспомогательная функция для построения клавиатуры с группами мышц и визуальной индикацией (для создания)"""
    keyboard_buttons = []
    
    for group in muscle_groups:
        # Получаем мышцы группы для проверки статуса
        group_muscles = await machine_management_use_case.get_muscles_by_group_id(group.id)
        group_muscle_ids = [m.id for m in group_muscles] if group_muscles else []
        
        # Проверяем, все ли мышцы группы выбраны
        all_selected = all(mid in selected_muscle_ids for mid in group_muscle_ids) if group_muscle_ids else False
        some_selected = any(mid in selected_muscle_ids for mid in group_muscle_ids) if group_muscle_ids else False
        
        # Выбираем эмодзи в зависимости от статуса
        if all_selected:
            emoji = "✅"
        elif some_selected:
            emoji = "🟡"
        else:
            emoji = "📦"
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {group.name}",
                callback_data=f"select_group_{group.id}"
            )
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(
            text="🔍 Выбрать отдельные мышцы",
            callback_data="select_individual_muscles"
        )
    ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="✅ Завершить и создать тренажер", callback_data="finish_machine_creation")
    ])
    keyboard_buttons.append([
        InlineKeyboardButton(text="⏭️ Пропустить (без мышц)", callback_data="skip_muscle_selection")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


@router.callback_query(F.data.startswith("edit_machine_muscles_"))
async def edit_machine_muscles_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик редактирования мышц тренажера - показывает меню выбора"""
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
        keyboard = await _build_muscle_groups_keyboard(muscle_groups, current_muscle_ids, machine_id, machine_management_use_case)
        
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
    """Обработчик выбора группы мышц при редактировании - переключает все мышцы группы (добавляет/удаляет)"""
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
        keyboard = await _build_muscle_groups_keyboard(muscle_groups, selected_muscle_ids, machine_id, machine_management_use_case)
        
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
    """Обработчик выбора отдельных мышц при редактировании - показывает список всех мышц"""
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
        
        # Группируем мышцы по группам
        muscles_by_group: dict = {}
        for muscle in all_muscles:
            group_name = muscle.group.name if muscle.group else "Без группы"
            if group_name not in muscles_by_group:
                muscles_by_group[group_name] = []
            muscles_by_group[group_name].append(muscle)
        
        # Создаем клавиатуру с мышцами (максимум 8 кнопок в ряд для удобства)
        keyboard_buttons = []
        for group_name, muscles in muscles_by_group.items():
            # Добавляем заголовок группы (если есть несколько групп)
            if len(muscles_by_group) > 1:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"📦 {group_name}",
                        callback_data="muscle_group_header"  # Неактивная кнопка
                    )
                ])
            
            # Добавляем мышцы группы (по 2 в ряд)
            for i in range(0, len(muscles), 2):
                row = []
                muscle = muscles[i]
                is_selected = muscle.id in selected_muscle_ids
                row.append(InlineKeyboardButton(
                    text=f"{'✓' if is_selected else '○'} {muscle.name[:20]}",
                    callback_data=f"toggle_edit_muscle_{muscle.id}"
                ))
                if i + 1 < len(muscles):
                    muscle2 = muscles[i+1]
                    is_selected2 = muscle2.id in selected_muscle_ids
                    row.append(InlineKeyboardButton(
                        text=f"{'✓' if is_selected2 else '○'} {muscle2.name[:20]}",
                        callback_data=f"toggle_edit_muscle_{muscle2.id}"
                    ))
                keyboard_buttons.append(row)
        
        # Добавляем кнопки управления
        keyboard_buttons.append([
            InlineKeyboardButton(text="✅ Сохранить изменения", callback_data="save_machine_muscles")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬅️ Назад к выбору", callback_data=f"edit_machine_muscles_{machine_id}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
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
    """Обработчик переключения выбора мышцы при редактировании"""
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
    """Обработчик сохранения изменений мышц тренажера"""
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
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_machine_menu_{machine.id}")],
                [InlineKeyboardButton(text="Архивировать", callback_data=f"archive_machine_{machine.id}")],
                [InlineKeyboardButton(text="Назад к списку", callback_data="list_machines")]
            ])
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


@router.callback_query(F.data.startswith("edit_machine_menu_"))
async def edit_machine_callback(
    callback: CallbackQuery, 
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик входа в режим редактирования тренажера"""
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
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить название", callback_data=f"edit_machine_name_{machine_id}")],
            [InlineKeyboardButton(text="Изменить фото", callback_data=f"edit_machine_photo_{machine_id}")],
            [InlineKeyboardButton(text="Редактировать мышцы", callback_data=f"edit_machine_muscles_{machine_id}")],
            [InlineKeyboardButton(text="Отмена", callback_data=f"view_machine_{machine.id}")]
        ])
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
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_machine_menu_{machine.id}")],
                [InlineKeyboardButton(text="Архивировать", callback_data=f"archive_machine_{machine.id}")],
                [InlineKeyboardButton(text="Назад к списку", callback_data="list_machines")]
            ])
            await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "skip_muscle_selection")
async def skip_muscle_selection_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик пропуска выбора мышц - создает тренажер без мышц"""
    user_id = callback.from_user.id
    try:
        data = await state.get_data()
        machine_name = data.get("machine_name")
        
        if not machine_name:
            await callback.message.edit_text("Ошибка: название тренажера не найдено.")
            await callback.answer()
            await state.clear()
            return
        
        new_machine = await machine_management_use_case.add_machine(user_id, machine_name, None, [])
        logger.info(f"Пользователь {user_id} успешно добавил тренажёр {new_machine.id} ({new_machine.name}) без мышц.")
        await callback.message.edit_text(f"Тренажер '{new_machine.name}' успешно добавлен!")
        await callback.answer()
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в skip_muscle_selection_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при создании тренажера.")
        await callback.answer()
        await state.clear()


@router.callback_query(F.data.startswith("select_group_"))
async def select_group_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик выбора группы мышц при создании - переключает все мышцы группы (добавляет/удаляет)"""
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
        machine_name = data.get("machine_name")
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        if not machine_name:
            await callback.message.edit_text("Ошибка: название тренажера не найдено.")
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
        
        # Получаем группы мышц для меню
        muscle_groups = await machine_management_use_case.get_all_muscle_groups()
        if not muscle_groups:
            await callback.message.edit_text("В базе данных нет групп мышц.")
            return
        
        # Создаем клавиатуру с визуальной индикацией
        keyboard = await _build_muscle_groups_keyboard_for_creation(muscle_groups, selected_muscle_ids, machine_management_use_case)
        
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
            f"Тренажер: {machine_name}\n\n"
            f"Выбранные мышцы ({len(selected_muscle_ids)}):\n{muscles_str}\n\n"
            "Выберите группы мышц или отдельные мышцы:"
        )
        
        if len(message_text) > 4096:
            message_text = (
                f"Тренажер: {machine_name}\n\n"
                f"Выбранные мышцы: {len(selected_muscle_ids)} шт.\n\n"
                "Выберите группы мышц или отдельные мышцы:"
            )
        
        await safe_edit_text(callback, message_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка в select_group_callback для пользователя {user_id}, группа {group_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при выборе группы мышц.")
        await callback.answer()


@router.callback_query(F.data == "select_individual_muscles")
async def select_individual_muscles_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик выбора отдельных мышц - показывает список всех мышц"""
    user_id = callback.from_user.id
    
    try:
        # Получаем все мышцы, сгруппированные по группам
        all_muscles = await machine_management_use_case.get_all_muscles()
        
        if not all_muscles:
            await callback.answer("В базе данных нет мышц.", show_alert=True)
            return
        
        # Получаем данные из FSM один раз
        data = await state.get_data()
        machine_name = data.get("machine_name", "Новый тренажер")
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        # Группируем мышцы по группам
        muscles_by_group: dict = {}
        for muscle in all_muscles:
            group_name = muscle.group.name if muscle.group else "Без группы"
            if group_name not in muscles_by_group:
                muscles_by_group[group_name] = []
            muscles_by_group[group_name].append(muscle)
        
        # Создаем клавиатуру с мышцами (максимум 8 кнопок в ряд для удобства)
        keyboard_buttons = []
        for group_name, muscles in muscles_by_group.items():
            # Добавляем заголовок группы (если есть несколько групп)
            if len(muscles_by_group) > 1:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"📦 {group_name}",
                        callback_data="muscle_group_header"  # Неактивная кнопка
                    )
                ])
            
            # Добавляем мышцы группы (по 2 в ряд)
            for i in range(0, len(muscles), 2):
                row = []
                muscle = muscles[i]
                is_selected = muscle.id in selected_muscle_ids
                row.append(InlineKeyboardButton(
                    text=f"{'✓' if is_selected else '○'} {muscle.name[:20]}",
                    callback_data=f"toggle_muscle_{muscle.id}"
                ))
                if i + 1 < len(muscles):
                    muscle2 = muscles[i+1]
                    is_selected2 = muscle2.id in selected_muscle_ids
                    row.append(InlineKeyboardButton(
                        text=f"{'✓' if is_selected2 else '○'} {muscle2.name[:20]}",
                        callback_data=f"toggle_muscle_{muscle2.id}"
                    ))
                keyboard_buttons.append(row)
        
        # Добавляем кнопки управления
        keyboard_buttons.append([
            InlineKeyboardButton(text="✅ Завершить и создать тренажер", callback_data="finish_machine_creation")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬅️ Назад к выбору групп", callback_data="add_more_muscles")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        selected_muscles = await machine_management_use_case.get_muscles_by_ids(selected_muscle_ids) if selected_muscle_ids else []
        selected_names = ", ".join([m.name for m in selected_muscles]) if selected_muscles else "Нет"
        
        await callback.message.edit_text(
            f"Тренажер: {machine_name}\n\n"
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
    """Обработчик переключения выбора отдельной мышцы"""
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
    """Обработчик для возврата к выбору мышц"""
    user_id = callback.from_user.id
    
    try:
        # Получаем группы мышц
        muscle_groups = await machine_management_use_case.get_all_muscle_groups()
        
        if not muscle_groups:
            await callback.answer("В базе данных нет групп мышц.", show_alert=True)
            return
        
        data = await state.get_data()
        machine_name = data.get("machine_name", "Новый тренажер")
        selected_muscle_ids = data.get("selected_muscle_ids", [])
        
        # Создаем клавиатуру с визуальной индикацией
        keyboard = await _build_muscle_groups_keyboard_for_creation(muscle_groups, selected_muscle_ids, machine_management_use_case)
        
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
            f"Выбранные мышцы ({len(selected_muscle_ids)}):\n{muscles_str}\n\n"
            "Выберите группы мышц или отдельные мышцы:"
        )
        
        if len(message_text) > 4096:
            message_text = (
                f"Тренажер: {machine_name}\n\n"
                f"Выбранные мышцы: {len(selected_muscle_ids)} шт.\n\n"
                "Выберите группы мышц или отдельные мышцы:"
            )
        
        await safe_edit_text(callback, message_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в add_more_muscles_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка.")
        await callback.answer()


@router.callback_query(F.data == "muscle_group_header")
async def muscle_group_header_callback(
    callback: CallbackQuery,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик неактивной кнопки заголовка группы - просто отвечает пустым ответом"""
    await callback.answer()


@router.callback_query(F.data == "finish_machine_creation")
async def finish_machine_creation_callback(
    callback: CallbackQuery,
    state: FSMContext,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик завершения создания тренажера"""
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
            user_id, machine_name, None, selected_muscle_ids
        )
        
        logger.info(
            f"Пользователь {user_id} успешно добавил тренажёр {new_machine.id} "
            f"({new_machine.name}) с {len(selected_muscle_ids)} мышцами."
        )
        
        muscles_str = "Не указаны"
        if selected_muscle_ids:
            selected_muscles = await machine_management_use_case.get_muscles_by_ids(selected_muscle_ids)
            muscles_str = ", ".join([m.name for m in selected_muscles])
        
        await callback.message.edit_text(
            f"✅ Тренажер '{new_machine.name}' успешно добавлен!\n\n"
            f"Мышцы: {muscles_str}"
        )
        await callback.answer()
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в finish_machine_creation_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при создании тренажера.")
        await callback.answer()
        await state.clear()


# Обработчик кнопки меню
@router.message(F.text == "💪 Тренажеры")
async def handle_machines_button(
    message: Message,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик кнопки 'Тренажеры'."""
    await cmd_machines(message, machine_management_use_case)