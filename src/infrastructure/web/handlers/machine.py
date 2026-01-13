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
        logger.info(f"User {message.from_user.id} used /machines command.")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить тренажер", callback_data="add_machine")],
            [InlineKeyboardButton(text="Мои тренажеры", callback_data="list_machines")]
        ])
        await message.answer("Управление тренажерами:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in cmd_machines for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке команды /machines.")


@router.callback_query(F.data == "add_machine")
async def add_machine_callback(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        logger.info(f"User {callback.from_user.id} initiated add_machine process.")
        await callback.message.edit_text("Введите название нового тренажера:")
        await state.set_state(MachineStates.waiting_for_machine_name)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in add_machine_callback for user {callback.from_user.id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при начале добавления тренажера.")
        await callback.answer()


@router.message(MachineStates.waiting_for_machine_name)
async def process_machine_name(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    machine_name = message.text.strip()
    
    try:
        if not machine_name:
            logger.warning(f"User {user_id} submitted empty machine name.")
            await message.answer("Название тренажера не может быть пустым. Попробуйте еще раз.")
            return

        existing_machine = await machine_management_use_case.machine_repository.get_user_machine_by_name(user_id, machine_name)
        if existing_machine:
            logger.warning(f"User {user_id} tried to add duplicate machine name: {machine_name}")
            await message.answer(f"Тренажер с названием '{machine_name}' уже существует. Попробуйте другое название.")
            return

        new_machine = await machine_management_use_case.add_machine(user_id, machine_name, None, [])
        logger.info(f"User {user_id} successfully added machine {new_machine.id} ({new_machine.name}).")
        await message.answer(f"Тренажер '{new_machine.name}' успешно добавлен!")

    except ValueError as e:
        logger.warning(f"Validation error when user {user_id} added machine: {e}")
        await message.answer(f"Ошибка: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in process_machine_name for user {user_id}: {e}", exc_info=True)
        await message.answer(f"Произошла непредвиденная ошибка: {e}")
    finally:
        await state.clear()
        logger.debug(f"State cleared for user {user_id}.")


@router.callback_query(F.data == "list_machines")
async def list_machines_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    try:
        machines = await machine_management_use_case.get_user_machines(user_id)

        if not machines:
            logger.info(f"User {user_id} requested machine list, none found.")
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
        logger.info(f"User {user_id} viewed list of {len(machines)} machines.")

    except Exception as e:
        logger.error(f"Error in list_machines_callback for user {user_id}: {e}", exc_info=True)
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
            logger.warning(f"User {user_id} tried to view non-existent or unauthorized machine {machine_id}.")
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
        logger.info(f"User {user_id} viewed details for machine {machine_id}.")

    except Exception as e:
        logger.error(f"Error in view_machine_details_callback for user {user_id}, machine {machine_id}: {e}", exc_info=True)
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
            logger.info(f"User {user_id} successfully archived machine {machine_id}.")
        else:
            await callback.message.edit_text(f"Не удалось архивировать тренажер {machine_id}. Возможно, он уже архивирован или не найден.")
            logger.warning(f"User {user_id} failed to archive machine {machine_id}.")
    except Exception as e:
        logger.error(f"Error in archive_machine_callback for user {user_id}, machine {machine_id}: {e}", exc_info=True)
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
            logger.warning(f"User {user_id} tried to edit non-existent or unauthorized machine {machine_id}.")
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
        logger.info(f"User {user_id} entered edit mode for machine {machine_id}.")

    except Exception as e:
        logger.error(f"Error in edit_machine_callback for user {user_id}, machine {machine_id}: {e}", exc_info=True)
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
        logger.info(f"User {user_id} editing name for machine {machine_id}.")
    except Exception as e:
        logger.error(f"Error in edit_machine_name_callback for user {user_id}, machine {machine_id}: {e}", exc_info=True)
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
            logger.warning(f"User {user_id} submitted empty new name for machine {machine_id}.")
            await message.answer("Название тренажера не может быть пустым. Попробуйте еще раз.")
            await state.set_state(MachineStates.waiting_for_edit_name) # Stay in state
            return

        updated_machine = await machine_management_use_case.update_machine(user_id, machine_id, name=new_name)
        if updated_machine:
            logger.info(f"User {user_id} successfully changed name of machine {machine_id} to '{new_name}'.")
            await message.answer(f"Название тренажера успешно изменено на '{updated_machine.name}'.")
        else:
            logger.warning(f"User {user_id} failed to change name of machine {machine_id} to '{new_name}'.")
            await message.answer("Не удалось изменить название тренажера.")
    except ValueError as e:
        logger.warning(f"Validation error when user {user_id} edited machine {machine_id} name: {e}")
        await message.answer(f"Ошибка: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in process_edit_machine_name for user {user_id}, machine {machine_id}: {e}", exc_info=True)
        await message.answer(f"Произошла непредвиденная ошибка: {e}")
    finally:
        await state.clear()
        # Re-display machine details
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