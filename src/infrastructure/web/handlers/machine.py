# ruff: noqa: F821
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


logger = logging.getLogger(__name__)

router = Router()

class MachineStates(StatesGroup):
    waiting_for_machine_name = State()
    waiting_for_machine_photo = State()
    waiting_for_muscle_selection = State()
    waiting_for_edit_name = State()
    waiting_for_edit_photo = State()

@router.message(Command("machines"))
async def cmd_machines(message: Message) -> None:
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
async def add_machine_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
async def process_machine_name(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    machine_name = message.text.strip()
    
    try:
        if not machine_name:
            logger.warning(f"Пользователь {user_id} отправил пустое название тренажёра.")
            await message.answer("Название тренажера не может быть пустым. Попробуйте еще раз.")
            return

        existing_machine = await machine_management_use_case.machine_repository.get_user_machine_by_name(user_id, machine_name)
        if existing_machine:
            logger.warning(f"Пользователь {user_id} попытался добавить дублирующееся название тренажёра: {machine_name}")
            await message.answer(f"Тренажер с названием '{machine_name}' уже существует. Попробуйте другое название.")
            return

        new_machine = await machine_management_use_case.add_machine(user_id, machine_name, None, [])
        logger.info(f"Пользователь {user_id} успешно добавил тренажёр {new_machine.id} ({new_machine.name}).")
        await message.answer(f"Тренажер '{new_machine.name}' успешно добавлен!")

    except ValueError as e:
        logger.warning(f"Ошибка валидации при добавлении тренажёра пользователем {user_id}: {e}")
        await message.answer(f"Ошибка: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в process_machine_name для пользователя {user_id}: {e}", exc_info=True)
        await message.answer(f"Произошла непредвиденная ошибка: {e}")
    finally:
        await state.clear()
        logger.debug(f"Состояние очищено для пользователя {user_id}.")


@router.callback_query(F.data == "list_machines")
async def list_machines_callback(callback: CallbackQuery) -> None:
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
async def view_machine_details_callback(callback: CallbackQuery) -> None:
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
            [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_machine_{machine.id}")],
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
async def archive_machine_callback(callback: CallbackQuery) -> None:
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


@router.callback_query(F.data.startswith("edit_machine_"))
async def edit_machine_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить название", callback_data=f"edit_machine_name_{machine_id}")],
            [InlineKeyboardButton(text="Изменить фото", callback_data=f"edit_machine_photo_{machine_id}")],
            [InlineKeyboardButton(text="Отмена", callback_data=f"view_machine_{machine.id}")]
        ])
        await callback.message.edit_text(f"Редактирование тренажера '{machine.name}':", reply_markup=keyboard)
        logger.info(f"Пользователь {user_id} вошёл в режим редактирования тренажёра {machine_id}.")

    except Exception as e:
        logger.error(f"Ошибка в edit_machine_callback для пользователя {user_id}, тренажёр {machine_id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при входе в режим редактирования.")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("edit_machine_name_"))
async def edit_machine_name_callback(callback: CallbackQuery, state: FSMContext) -> None:
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
async def process_edit_machine_name(message: Message, state: FSMContext) -> None:
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
                [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_machine_{machine.id}")],
                [InlineKeyboardButton(text="Архивировать", callback_data=f"archive_machine_{machine.id}")],
                [InlineKeyboardButton(text="Назад к списку", callback_data="list_machines")]
            ])
            await message.answer(text, reply_markup=keyboard)


# Обработчик кнопки меню
@router.message(F.text == "💪 Тренажеры")
async def handle_machines_button(message: Message) -> None:
    """Обработчик кнопки 'Тренажеры'."""
    await cmd_machines(message)