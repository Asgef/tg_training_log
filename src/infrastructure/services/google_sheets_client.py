import structlog
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

logger = structlog.get_logger(__name__)

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
            "Повторная попытка Google Sheets API",
            event_type="google_sheets_api_retry",
            attempt=retry_state.attempt_number,
            max_attempts=MAX_RETRY_ATTEMPTS,
            function=func.__name__,
            error=str(retry_state.outcome.exception()) if retry_state.outcome else "unknown",
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
                logger.error(
                    "Переменная окружения GOOGLE_CREDENTIALS_JSON не установлена",
                    event_type="google_sheets_init_error",
                    error="missing_credentials",
                )
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
                "GoogleSheetsClient успешно инициализирован",
                event_type="google_sheets_client_initialized",
                connect_timeout=CONNECT_TIMEOUT,
                read_timeout=READ_TIMEOUT,
            )
        except Exception as e:
            logger.critical(
                "Не удалось инициализировать GoogleSheetsClient",
                event_type="google_sheets_init_error",
                error=str(e),
                exc_info=True,
            )
            raise RuntimeError(f"Не удалось инициализировать GoogleSheetsClient: {e}")

    @retry_google_sheets_operation
    def open_spreadsheet(self, spreadsheet_id: str) -> gspread.Spreadsheet:
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            logger.debug(
                "Открыта Google таблица",
                event_type="google_sheets_spreadsheet_opened",
                spreadsheet_id=spreadsheet_id,
            )
            return spreadsheet
        except gspread.exceptions.SpreadsheetNotFound:
            logger.warning(
                "Таблица не найдена",
                event_type="google_sheets_api_error",
                error_type="SpreadsheetNotFound",
                spreadsheet_id=spreadsheet_id,
            )
            raise ValueError(f"Таблица с ID '{spreadsheet_id}' не найдена.")
        except gspread.exceptions.APIError as e:
            error_code = (
                getattr(e.response, "status_code", None)
                if hasattr(e, "response")
                else None
            )
            if error_code in (401, 403):
                logger.warning(
                    "Недостаточно прав для доступа к таблице",
                    event_type="google_sheets_access_denied",
                    spreadsheet_id=spreadsheet_id,
                    error_code=error_code,
                )
                raise PermissionError(
                    "Недостаточно прав для доступа к Google Sheets."
                ) from e
            logger.error(
                "Ошибка Google Sheets API при открытии таблицы",
                event_type="google_sheets_api_error",
                error_type="APIError",
                spreadsheet_id=spreadsheet_id,
                error_code=error_code,
                error=str(e),
                exc_info=True,
            )
            raise RuntimeError(f"Ошибка при открытии таблицы {spreadsheet_id}: {e}")
        except Exception as e:
            logger.error(
                "Неожиданная ошибка при открытии таблицы",
                event_type="google_sheets_error",
                spreadsheet_id=spreadsheet_id,
                error=str(e),
                exc_info=True,
            )
            raise RuntimeError(f"Ошибка при открытии таблицы {spreadsheet_id}: {e}")

    def _normalize_header_row(self, values: List[str], total_cols: int) -> List[str]:
        if len(values) >= total_cols:
            return values[:total_cols]
        return values + [""] * (total_cols - len(values))

    @retry_google_sheets_operation
    def get_or_create_worksheet(
        self,
        spreadsheet: gspread.Spreadsheet,
        worksheet_name: str,
        sheet_title: str,
        headers_ru: List[str],
        headers: List[str],
    ) -> gspread.Worksheet:
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            total_cols = len(headers)
            title_row = self._normalize_header_row([sheet_title], total_cols)
            headers_ru_row = self._normalize_header_row(headers_ru, total_cols)
            headers_row = self._normalize_header_row(headers, total_cols)
            if not worksheet.row_values(1):
                worksheet.update([title_row, headers_ru_row, headers_row])
                logger.info(
                    "Созданы заголовки в листе",
                    event_type="google_sheets_headers_created",
                    worksheet_name=worksheet_name,
                )
            else:
                worksheet.update("A1", [title_row, headers_ru_row, headers_row])
            logger.debug(
                "Получен/Создан лист",
                event_type="google_sheets_worksheet_accessed",
                worksheet_name=worksheet_name,
            )
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name, rows=3, cols=len(headers)
            )
            total_cols = len(headers)
            title_row = self._normalize_header_row([sheet_title], total_cols)
            headers_ru_row = self._normalize_header_row(headers_ru, total_cols)
            headers_row = self._normalize_header_row(headers, total_cols)
            worksheet.update([title_row, headers_ru_row, headers_row])
            logger.info(
                "Лист создан с заголовками",
                event_type="google_sheets_worksheet_created",
                worksheet_name=worksheet_name,
            )
            return worksheet
        except gspread.exceptions.APIError as e:
            logger.error(
                "Ошибка Google Sheets API при получении/создании листа",
                event_type="google_sheets_api_error",
                error_type="APIError",
                worksheet_name=worksheet_name,
                error_code=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                error=str(e),
                exc_info=True,
            )
            raise RuntimeError(
                f"Ошибка при получении/создании листа '{worksheet_name}': {e}"
            )
        except Exception as e:
            logger.error(
                "Ошибка при получении/создании листа",
                event_type="google_sheets_error",
                worksheet_name=worksheet_name,
                error=str(e),
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
        sheet_title: str,
        headers_ru: List[str],
        headers: List[str],
        data: List[List[Any]],
    ) -> None:
        try:
            spreadsheet = self.open_spreadsheet(spreadsheet_id)
            worksheet = self.get_or_create_worksheet(
                spreadsheet, worksheet_name, sheet_title, headers_ru, headers
            )
            worksheet.append_rows(data)
            logger.info(
                "Добавлены строки в Google Sheets",
                event_type="google_sheets_data_appended",
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                rows_count=len(data),
            )
        except gspread.exceptions.APIError as e:
            logger.error(
                "Ошибка Google Sheets API при добавлении данных",
                event_type="google_sheets_api_error",
                error_type="APIError",
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                error_code=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                error=str(e),
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Ошибка при добавлении данных в Google Sheets",
                event_type="google_sheets_error",
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                error=str(e),
                exc_info=True,
            )
            raise

    @retry_google_sheets_operation
    def upsert_dataframe(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        sheet_title: str,
        headers_ru: List[str],
        df: pd.DataFrame,
        key_column: str,
    ) -> None:
        try:
            spreadsheet = self.open_spreadsheet(spreadsheet_id)
            worksheet = self.get_or_create_worksheet(
                spreadsheet,
                worksheet_name,
                sheet_title,
                headers_ru,
                df.columns.tolist(),
            )

            existing_data = worksheet.get_all_records(head=3)
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
                    "A3",
                    [merged_df.columns.values.tolist()] + merged_df.values.tolist(),
                )
                logger.info(
                    "Обновлено/добавлено строк в Google Sheets",
                    event_type="google_sheets_data_upserted",
                    spreadsheet_id=spreadsheet_id,
                    worksheet_name=worksheet_name,
                    rows_count=len(df),
                    key_column=key_column,
                )

            else:
                worksheet.update(
                    "A3", [df.columns.values.tolist()] + df.values.tolist()
                )
                logger.info(
                    "Записаны новые строки в Google Sheets",
                    event_type="google_sheets_data_inserted",
                    spreadsheet_id=spreadsheet_id,
                    worksheet_name=worksheet_name,
                    rows_count=len(df),
                )
        except gspread.exceptions.APIError as e:
            logger.error(
                "Ошибка Google Sheets API при обновлении/добавлении dataframe",
                event_type="google_sheets_api_error",
                error_type="APIError",
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                error_code=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                error=str(e),
                exc_info=True,
            )
            raise

    @retry_google_sheets_operation
    def replace_worksheet_data(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        sheet_title: str,
        headers_ru: List[str],
        headers: List[str],
        data: List[List[Any]],
    ) -> None:
        """Полностью перезаписывает лист, сохраняя 3 строки заголовков."""
        try:
            spreadsheet = self.open_spreadsheet(spreadsheet_id)
            worksheet = self.get_or_create_worksheet(
                spreadsheet, worksheet_name, sheet_title, headers_ru, headers
            )
            total_cols = len(headers)
            title_row = self._normalize_header_row([sheet_title], total_cols)
            headers_ru_row = self._normalize_header_row(headers_ru, total_cols)
            headers_row = self._normalize_header_row(headers, total_cols)
            rows = [title_row, headers_ru_row, headers_row] + data
            worksheet.clear()
            worksheet.resize(rows=max(len(rows), 3), cols=total_cols)
            worksheet.update(rows)
            logger.info(
                "Лист полностью перезаписан",
                event_type="google_sheets_sheet_replaced",
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                rows_count=len(data),
            )
        except gspread.exceptions.APIError as e:
            logger.error(
                "Ошибка Google Sheets API при полной перезаписи листа",
                event_type="google_sheets_api_error",
                error_type="APIError",
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                error_code=getattr(e.response, "status_code", None)
                if hasattr(e, "response")
                else None,
                error=str(e),
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Ошибка при полной перезаписи листа",
                event_type="google_sheets_error",
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                error=str(e),
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "Ошибка при обновлении/добавлении dataframe в Google Sheets",
                event_type="google_sheets_error",
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                error=str(e),
                exc_info=True,
            )
            raise
