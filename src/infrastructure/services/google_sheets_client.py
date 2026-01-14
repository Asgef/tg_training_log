import logging
from functools import wraps
from typing import List, Any, Callable, TypeVar, cast

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from src.configs.config import config

logger = logging.getLogger(__name__)

# Типы для таймаутов (connect, read) в секундах
CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 30.0
MAX_RETRY_ATTEMPTS = 3
MIN_RETRY_WAIT = 1.0  # секунды
MAX_RETRY_WAIT = 60.0  # секунды

# Тип для generic функций
F = TypeVar("F", bound=Callable[..., Any])


def is_retryable_error(exception: Exception) -> bool:
    """Определяет, можно ли повторить запрос при данной ошибке.
    
    Retryable ошибки:
    - Rate limit (429)
    - Временные сетевые ошибки (timeout, connection errors)
    - Временные ошибки сервера (5xx)
    
    Non-retryable ошибки:
    - Ошибки аутентификации (401, 403)
    - Ошибки валидации (400)
    - Ошибки "не найдено" (404)
    - Ошибки бизнес-логики (ValueError для несуществующих таблиц)
    """
    # Ошибки gspread, которые можно повторить
    if isinstance(exception, gspread.exceptions.APIError):
        # APIError содержит код ответа через response.status_code
        try:
            error_code = exception.response.status_code
            if error_code == 429:  # Rate limit
                return True
            if 500 <= error_code < 600:  # Server errors
                return True
            if error_code in (401, 403, 404):  # Auth/Not found - не повторяем
                return False
        except AttributeError:
            # Если response отсутствует, считаем ошибку не повторяемой
            return False
    
    # Сетевые ошибки - можно повторить
    if isinstance(exception, (TimeoutError, ConnectionError, OSError)):
        return True
    
    # Ошибки валидации и бизнес-логики - не повторяем
    if isinstance(exception, (ValueError, gspread.exceptions.SpreadsheetNotFound)):
        return False
    
    # По умолчанию для неизвестных ошибок - не повторяем
    # Но можно изменить на True, если нужно быть более агрессивным
    return False


def retry_google_sheets_operation(func: F) -> F:
    """Декоратор для retry операций с Google Sheets API.
    
    Использует exponential backoff и классификацию ошибок.
    """
    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=MIN_RETRY_WAIT, min=MIN_RETRY_WAIT, max=MAX_RETRY_WAIT),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Повторная попытка {retry_state.attempt_number}/{MAX_RETRY_ATTEMPTS} "
            f"для {func.__name__} после ошибки: {retry_state.outcome.exception()}"
        ) if retry_state.outcome else None,
    )
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)
    
    return cast(F, wrapper)


class GoogleSheetsClient:
    def __init__(self):
        try:
            if not config.google_credentials_json:
                logger.error("Переменная окружения GOOGLE_CREDENTIALS_JSON не установлена.")
                raise ValueError(
                    "Переменная окружения GOOGLE_CREDENTIALS_JSON не установлена."
                )

            creds_info = config.get_google_credentials_dict()
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            self.credentials = Credentials.from_service_account_info(
                creds_info, scopes=scopes
            )
            self.gc = gspread.authorize(self.credentials)
            
            # Устанавливаем таймауты для всех HTTP запросов
            # (connect_timeout, read_timeout)
            self.gc.set_timeout((CONNECT_TIMEOUT, READ_TIMEOUT))
            logger.info(
                f"GoogleSheetsClient успешно инициализирован с таймаутами "
                f"(connect={CONNECT_TIMEOUT}s, read={READ_TIMEOUT}s)."
            )
        except Exception as e:
            logger.critical(
                f"Не удалось инициализировать GoogleSheetsClient: {e}", exc_info=True
            )
            raise RuntimeError(f"Не удалось инициализировать GoogleSheetsClient: {e}")

    @retry_google_sheets_operation
    def open_spreadsheet(self, spreadsheet_id: str):
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            logger.debug(f"Открыта Google таблица с ID: {spreadsheet_id}")
            return spreadsheet
        except gspread.exceptions.SpreadsheetNotFound:
            logger.warning(f"Таблица с ID '{spreadsheet_id}' не найдена.")
            raise ValueError(f"Таблица с ID '{spreadsheet_id}' не найдена.")
        except Exception as e:
            logger.error(
                f"Ошибка при открытии таблицы {spreadsheet_id}: {e}", exc_info=True
            )
            raise RuntimeError(f"Ошибка при открытии таблицы {spreadsheet_id}: {e}")

    @retry_google_sheets_operation
    def get_or_create_worksheet(
        self, spreadsheet, worksheet_name: str, headers: List[str]
    ):
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            if not worksheet.row_values(1):
                worksheet.insert_row(headers, 1)
                logger.info(f"Созданы заголовки в листе '{worksheet_name}'.")
            logger.debug(f"Получен/Создан лист '{worksheet_name}'.")
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name, rows=1, cols=len(headers)
            )
            worksheet.insert_row(headers, 1)
            logger.info(f"Лист '{worksheet_name}' создан с заголовками.")
            return worksheet
        except Exception as e:
            logger.error(
                f"Ошибка при получении/создании листа '{worksheet_name}': {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Ошибка при получении/создании листа '{worksheet_name}': {e}"
            )

    @retry_google_sheets_operation
    def append_data(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        data: List[List[Any]],
        headers: List[str],
    ):
        try:
            spreadsheet = self.open_spreadsheet(spreadsheet_id)
            worksheet = self.get_or_create_worksheet(
                spreadsheet, worksheet_name, headers
            )
            worksheet.append_rows(data)
            logger.info(
                f"Добавлено {len(data)} строк в '{worksheet_name}' в таблице {spreadsheet_id}."
            )
        except Exception as e:
            logger.error(
                f"Ошибка при добавлении данных в '{worksheet_name}' в таблице {spreadsheet_id}: {e}",
                exc_info=True,
            )
            raise

    @retry_google_sheets_operation
    def upsert_dataframe(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        df: pd.DataFrame,
        key_column: str,
    ):
        try:
            spreadsheet = self.open_spreadsheet(spreadsheet_id)
            worksheet = self.get_or_create_worksheet(
                spreadsheet, worksheet_name, df.columns.tolist()
            )

            existing_data = worksheet.get_all_records()
            existing_df = pd.DataFrame(existing_data)

            if not existing_df.empty and key_column in existing_df.columns:
                existing_df[key_column] = existing_df[key_column].astype(
                    df[key_column].dtype
                )
                merged_df = pd.merge(
                    existing_df, df, on=key_column, how="outer", suffixes=("_old", "")
                )

                for col in df.columns:
                    if col != key_column:
                        merged_df[col] = merged_df[col].fillna(merged_df[col + "_old"])

                merged_df = merged_df.drop(
                    columns=[
                        col + "_old"
                        for col in df.columns
                        if col + "_old" in merged_df.columns
                    ]
                )

                worksheet.update(
                    [merged_df.columns.values.tolist()] + merged_df.values.tolist()
                )
                logger.info(
                    f"Обновлено/добавлено {len(df)} строк в '{worksheet_name}' в таблице {spreadsheet_id} с ключом '{key_column}'."
                )

            else:
                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
                logger.info(
                    f"Записано {len(df)} новых строк в '{worksheet_name}' в таблице {spreadsheet_id}."
                )
        except Exception as e:
            logger.error(
                f"Ошибка при обновлении/добавлении dataframe в '{worksheet_name}' в таблице {spreadsheet_id}: {e}",
                exc_info=True,
            )
            raise
