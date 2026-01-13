# ruff: noqa: F821
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


logger = logging.getLogger(__name__)

router = Router()

class GoogleSheetsStates(StatesGroup):
    waiting_for_sheet_url = State()

@router.message(Command("google_sheets"))
async def cmd_google_sheets(message: Message) -> None:
    try:
        logger.info(f"User {message.from_user.id} used /google_sheets command.")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Настроить Google Sheets", callback_data="setup_google_sheets")],
            [InlineKeyboardButton(text="Экспортировать данные", callback_data="export_data_to_sheets")]
        ])
        await message.answer("Управление Google Sheets:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in cmd_google_sheets for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке команды /google_sheets.")

@router.callback_query(F.data == "setup_google_sheets")
async def setup_google_sheets_callback(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        logger.info(f"User {callback.from_user.id} initiated Google Sheets setup.")
        await callback.message.edit_text("Пожалуйста, предоставьте URL вашей Google Sheet. Убедитесь, что сервисный аккаунт имеет доступ на запись.")
        await state.set_state(GoogleSheetsStates.waiting_for_sheet_url)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in setup_google_sheets_callback for user {callback.from_user.id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при начале настройки Google Sheets.")
        await callback.answer()

@router.message(GoogleSheetsStates.waiting_for_sheet_url)
async def process_sheet_url(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    sheet_url = message.text.strip()

    try:
        logger.info(f"User {user_id} submitted Google Sheet URL for setup.")
        success = await google_sheets_export_use_case.setup_google_sheets_config(user_id, sheet_url)
        if success:
            await message.answer("Google Sheets успешно настроены.")
            logger.info(f"User {user_id} successfully configured Google Sheets.")
        else:
            await message.answer("Не удалось настроить Google Sheets.")
            logger.warning(f"User {user_id} failed to configure Google Sheets for URL: {sheet_url}.")
    except ValueError as e:
        logger.warning(f"Validation error during Google Sheets setup for user {user_id}, URL {sheet_url}: {e}")
        await message.answer(f"Ошибка: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in process_sheet_url for user {user_id}, URL {sheet_url}: {e}", exc_info=True)
        await message.answer(f"Произошла непредвиденная ошибка: {e}")
    finally:
        await state.clear()
        logger.debug(f"State cleared for user {user_id}.")

@router.callback_query(F.data == "export_data_to_sheets")
async def export_data_to_sheets_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await callback.message.edit_text("Начинаю экспорт данных в Google Sheets...")
    try:
        logger.info(f"User {user_id} initiated data export to Google Sheets.")
        success = await google_sheets_export_use_case.export_data_to_sheets(user_id)
        if success:
            await callback.message.edit_text("Данные успешно экспортированы в Google Sheets.")
            logger.info(f"User {user_id} successfully exported data to Google Sheets.")
        else:
            await callback.message.edit_text("Не удалось экспортировать данные.")
            logger.warning(f"User {user_id} failed to export data to Google Sheets.")
    except ValueError as e:
        logger.warning(f"Validation error during Google Sheets export for user {user_id}: {e}")
        await callback.message.edit_text(f"Ошибка экспорта: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in export_data_to_sheets_callback for user {user_id}: {e}", exc_info=True)
        await callback.message.edit_text(f"Произошла непредвиденная ошибка при экспорте: {e}")
    finally:
        await callback.answer()