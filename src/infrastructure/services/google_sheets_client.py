import json
import os
import logging
from typing import List, Any

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    def __init__(self):
        try:
            creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
            if not creds_json:
                logger.error("Переменная окружения GOOGLE_CREDENTIALS_JSON не установлена.")
                raise ValueError(
                    "Переменная окружения GOOGLE_CREDENTIALS_JSON не установлена."
                )

            creds_info = json.loads(creds_json)
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            self.credentials = Credentials.from_service_account_info(
                creds_info, scopes=scopes
            )
            self.gc = gspread.authorize(self.credentials)
            logger.info("GoogleSheetsClient успешно инициализирован.")
        except Exception as e:
            logger.critical(
                f"Не удалось инициализировать GoogleSheetsClient: {e}", exc_info=True
            )
            raise RuntimeError(f"Не удалось инициализировать GoogleSheetsClient: {e}")

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
