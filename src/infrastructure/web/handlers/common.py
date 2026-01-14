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
        logger.info(f"Пользователь {message.from_user.id} использовал команду /google_sheets.")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Настроить Google Sheets", callback_data="setup_google_sheets")],
            [InlineKeyboardButton(text="Экспортировать данные", callback_data="export_data_to_sheets")]
        ])
        await message.answer("Управление Google Sheets:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в cmd_google_sheets для пользователя {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке команды /google_sheets.")

@router.callback_query(F.data == "setup_google_sheets")
async def setup_google_sheets_callback(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        logger.info(f"Пользователь {callback.from_user.id} инициировал настройку Google Sheets.")
        await callback.message.edit_text(
            "📊 Настройка Google Sheets\n\n"
            "Для подключения таблицы предоставьте доступ сервисному аккаунту и отправьте ссылку на таблицу.\n\n"
            "📋 Шаги:\n\n"
            "1️⃣ Откройте вашу Google Таблицу в браузере.\n"
            "2️⃣ Нажмите кнопку \"Настроить доступ\" (Share) в правом верхнем углу.\n"
            "3️⃣ В поле \"Добавить людей и группы\" вставьте адрес сервисного аккаунта:\n"
            "   `tg-training@tgtraining.iam.gserviceaccount.com`\n"
            "4️⃣ Выберите уровень доступа: \"Редактор\" (Editor).\n"
            "5️⃣ Нажмите \"Отправить\" (Send).\n"
            "6️⃣ Скопируйте URL таблицы из адресной строки браузера (формат: `https://docs.google.com/spreadsheets/d/...`) и отправьте его боту.\n\n"
            "После этого бот сможет экспортировать ваши данные в таблицу."
        )
        await state.set_state(GoogleSheetsStates.waiting_for_sheet_url)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в setup_google_sheets_callback для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при начале настройки Google Sheets.")
        await callback.answer()

@router.message(GoogleSheetsStates.waiting_for_sheet_url)
async def process_sheet_url(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    sheet_url = message.text.strip()

    try:
        logger.info(f"Пользователь {user_id} отправил URL Google Sheet для настройки.")
        success = await google_sheets_export_use_case.setup_google_sheets_config(user_id, sheet_url)
        if success:
            await message.answer("Google Sheets успешно настроены.")
            logger.info(f"Пользователь {user_id} успешно настроил Google Sheets.")
        else:
            await message.answer("Не удалось настроить Google Sheets.")
            logger.warning(f"Пользователь {user_id} не смог настроить Google Sheets для URL: {sheet_url}.")
    except ValueError as e:
        logger.warning(f"Ошибка валидации при настройке Google Sheets для пользователя {user_id}, URL {sheet_url}: {e}")
        await message.answer(f"Ошибка: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в process_sheet_url для пользователя {user_id}, URL {sheet_url}: {e}", exc_info=True)
        await message.answer(f"Произошла непредвиденная ошибка: {e}")
    finally:
        await state.clear()
        logger.debug(f"Состояние очищено для пользователя {user_id}.")

@router.callback_query(F.data == "export_data_to_sheets")
async def export_data_to_sheets_callback(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await callback.message.edit_text("Начинаю экспорт данных в Google Sheets...")
    try:
        logger.info(f"Пользователь {user_id} инициировал экспорт данных в Google Sheets.")
        success = await google_sheets_export_use_case.export_data_to_sheets(user_id)
        if success:
            await callback.message.edit_text("Данные успешно экспортированы в Google Sheets.")
            logger.info(f"Пользователь {user_id} успешно экспортировал данные в Google Sheets.")
        else:
            await callback.message.edit_text("Не удалось экспортировать данные.")
            logger.warning(f"Пользователь {user_id} не смог экспортировать данные в Google Sheets.")
    except ValueError as e:
        logger.warning(f"Ошибка валидации при экспорте Google Sheets для пользователя {user_id}: {e}")
        await callback.message.edit_text(f"Ошибка экспорта: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в export_data_to_sheets_callback для пользователя {user_id}: {e}", exc_info=True)
        await callback.message.edit_text(f"Произошла непредвиденная ошибка при экспорте: {e}")
    finally:
        await callback.answer()


# Обработчик кнопки меню
@router.message(F.text == "📊 Google Sheets")
async def handle_google_sheets_button(message: Message) -> None:
    """Обработчик кнопки 'Google Sheets'."""
    await cmd_google_sheets(message)


# Обработчик кнопки меню
@router.message(F.text == "📊 Google Sheets")
async def handle_google_sheets_button(message: Message) -> None:
    """Обработчик кнопки 'Google Sheets'."""
    await cmd_google_sheets(message)