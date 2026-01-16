"""Handler для общих команд (Google Sheets и т.д.)."""
import structlog
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.application.use_case_interfaces import IGoogleSheetsExportUseCase

logger = structlog.get_logger(__name__)

router = Router()
SERVICE_ACCOUNT_EMAIL = "tg-training@tgtraining.iam.gserviceaccount.com"

class GoogleSheetsStates(StatesGroup):
    waiting_for_sheet_url = State()

@router.message(Command("google_sheets"))
async def cmd_google_sheets(message: Message) -> None:
    try:
        logger.info(
            "Пользователь использовал команду /google_sheets",
            event_type="google_sheets_command",
            user_id=message.from_user.id,
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Настроить Google Sheets", callback_data="setup_google_sheets")],
            [InlineKeyboardButton(text="Экспортировать данные", callback_data="export_data_to_sheets")]
        ])
        await message.answer("Управление Google Sheets:", reply_markup=keyboard)
    except Exception as e:
        logger.error(
            "Ошибка в cmd_google_sheets",
            event_type="google_sheets_command_error",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await message.answer("Произошла ошибка при обработке команды /google_sheets.")

@router.callback_query(F.data == "setup_google_sheets")
async def setup_google_sheets_callback(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        logger.info(
            "Пользователь инициировал настройку Google Sheets",
            event_type="google_sheets_setup_started",
            user_id=callback.from_user.id,
        )
        await callback.message.edit_text(
            "📊 Настройка Google Sheets\n\n"
            "Для подключения таблицы предоставьте доступ сервисному аккаунту и отправьте ссылку на таблицу.\n\n"
            "📋 Шаги:\n\n"
            "1️⃣ Откройте вашу Google Таблицу в браузере.\n"
            "2️⃣ Нажмите кнопку \"Настроить доступ\" (Share) в правом верхнем углу.\n"
            "3️⃣ В поле \"Добавить людей и группы\" вставьте адрес сервисного аккаунта:\n"
            f"   `{SERVICE_ACCOUNT_EMAIL}`\n"
            "4️⃣ Выберите уровень доступа: \"Редактор\" (Editor).\n"
            "5️⃣ Нажмите \"Отправить\" (Send).\n"
            "6️⃣ Скопируйте URL таблицы из адресной строки браузера (формат: `https://docs.google.com/spreadsheets/d/...`) и отправьте его боту.\n\n"
            "После этого бот сможет экспортировать ваши данные в таблицу."
        )
        await state.set_state(GoogleSheetsStates.waiting_for_sheet_url)
        await callback.answer()
    except Exception as e:
        logger.error(
            "Ошибка в setup_google_sheets_callback",
            event_type="google_sheets_setup_error",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await callback.message.answer("Произошла ошибка при начале настройки Google Sheets.")
        await callback.answer()

@router.message(GoogleSheetsStates.waiting_for_sheet_url)
async def process_sheet_url(
    message: Message,
    state: FSMContext,
    google_sheets_export_use_case: IGoogleSheetsExportUseCase,
) -> None:
    """Обработчик URL Google Sheets."""
    user_id = message.from_user.id
    sheet_url = message.text.strip()

    try:
        logger.info(
            "Пользователь отправил URL Google Sheet для настройки",
            event_type="google_sheets_url_submitted",
            user_id=user_id,
        )
        success = await google_sheets_export_use_case.setup_google_sheets_config(user_id, sheet_url)
        if success:
            logger.info(
                "Пользователь успешно настроил Google Sheets",
                event_type="google_sheets_setup_completed",
                user_id=user_id,
            )
            await message.answer("Google Sheets успешно настроены.")
        else:
            logger.warning(
                "Пользователь не смог настроить Google Sheets",
                event_type="google_sheets_setup_failed",
                user_id=user_id,
                reason="unknown",
            )
            await message.answer("Не удалось настроить Google Sheets.")
    except ValueError as e:
        logger.warning(
            "Ошибка валидации при настройке Google Sheets",
            event_type="google_sheets_setup_validation_error",
            user_id=user_id,
            error=str(e),
        )
        await message.answer(f"Ошибка: {e}")
    except Exception as e:
        logger.error(
            "Неожиданная ошибка в process_sheet_url",
            event_type="google_sheets_setup_error",
            user_id=user_id,
            error=str(e),
            exc_info=True,
        )
        await message.answer(f"Произошла непредвиденная ошибка: {e}")
    finally:
        await state.clear()

@router.callback_query(F.data == "export_data_to_sheets")
async def export_data_to_sheets_callback(
    callback: CallbackQuery,
    google_sheets_export_use_case: IGoogleSheetsExportUseCase,
) -> None:
    """Обработчик экспорта данных в Google Sheets."""
    user_id = callback.from_user.id
    await callback.message.edit_text("Начинаю экспорт данных в Google Sheets...")
    try:
        logger.info(
            "Пользователь инициировал экспорт данных в Google Sheets",
            event_type="google_sheets_export_started",
            user_id=user_id,
        )
        result = await google_sheets_export_use_case.export_data_to_sheets(user_id)
        if result is not None:
            logger.info(
                "Пользователь успешно экспортировал данные в Google Sheets",
                event_type="google_sheets_export_completed",
                user_id=user_id,
            )
            await callback.message.edit_text(
                "Данные успешно экспортированы в Google Sheets.\n"
                f"LOG_SETS: добавлено {result.get('sets_added', 0)} строк.\n"
                f"LOG_MUSCLES: добавлено {result.get('muscles_added', 0)} строк."
            )
        else:
            logger.warning(
                "Пользователь не смог экспортировать данные в Google Sheets",
                event_type="google_sheets_export_failed",
                user_id=user_id,
                reason="unknown",
            )
            await callback.message.edit_text("Не удалось экспортировать данные.")
    except PermissionError:
        await callback.message.edit_text(
            "Нет доступа к таблице. Дайте доступ редактора сервисному аккаунту:\n"
            f"`{SERVICE_ACCOUNT_EMAIL}`"
        )
    except ValueError as e:
        logger.warning(
            "Ошибка валидации при экспорте Google Sheets",
            event_type="google_sheets_export_validation_error",
            user_id=user_id,
            error=str(e),
        )
        await callback.message.edit_text(f"Ошибка экспорта: {e}")
    except Exception as e:
        logger.error(
            "Неожиданная ошибка в export_data_to_sheets_callback",
            event_type="google_sheets_export_error",
            user_id=user_id,
            error=str(e),
            exc_info=True,
        )
        await callback.message.edit_text(f"Произошла непредвиденная ошибка при экспорте: {e}")
    finally:
        await callback.answer()


# Обработчик кнопки меню
@router.message(F.text == "📊 Google Sheets")
async def handle_google_sheets_button(message: Message) -> None:
    """Обработчик кнопки 'Google Sheets'."""
    await cmd_google_sheets(message)