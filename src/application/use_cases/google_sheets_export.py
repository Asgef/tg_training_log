import structlog
from urllib.parse import urlparse

import pandas as pd

from src.application.repositories import (
    IUserRepository,
    IMachineRepository,
    ISetEntryRepository,
)
from src.application.use_case_interfaces import IGoogleSheetsExportUseCase
from src.infrastructure.services.google_sheets_client import GoogleSheetsClient

logger = structlog.get_logger(__name__)


class GoogleSheetsExportUseCase(IGoogleSheetsExportUseCase):
    def __init__(
        self,
        user_repository: IUserRepository,
        machine_repository: IMachineRepository,
        set_entry_repository: ISetEntryRepository,
        google_sheets_client: GoogleSheetsClient,
    ):
        self.user_repository = user_repository
        self.machine_repository = machine_repository
        self.set_entry_repository = set_entry_repository
        self.google_sheets_client = google_sheets_client

    async def setup_google_sheets_config(self, user_id: int, sheet_url: str) -> bool:
        try:
            parsed_url = urlparse(sheet_url)
            if "docs.google.com" not in parsed_url.netloc:
                logger.warning(
                    "Пользователь предоставил неверный URL Google Sheets",
                    event_type="google_sheets_invalid_url",
                    user_id=user_id,
                )
                raise ValueError("Предоставленный URL не является валидным URL Google Sheets.")

            path_parts = parsed_url.path.split("/")
            if "d" in path_parts:
                try:
                    spreadsheet_id = path_parts[path_parts.index("d") + 1]
                except IndexError:
                    logger.warning(
                        "Пользователь предоставил URL без определяемого ID таблицы",
                        event_type="google_sheets_url_parse_error",
                        user_id=user_id,
                    )
                    raise ValueError("Не удалось извлечь ID таблицы из URL.")
            else:
                logger.warning(
                    "Пользователь предоставил URL без определяемого ID таблицы",
                    event_type="google_sheets_url_parse_error",
                    user_id=user_id,
                )
                raise ValueError("Could not extract spreadsheet ID from the URL.")

            await self.user_repository.save_google_sheet_config(
                user_id, sheet_url, spreadsheet_id
            )
            logger.info(
                "Пользователь успешно настроил Google Sheets",
                event_type="google_sheets_config_saved",
                user_id=user_id,
                spreadsheet_id=spreadsheet_id,
            )
            return True
        except Exception as e:
            logger.error(
                "Ошибка при настройке конфигурации Google Sheets",
                event_type="google_sheets_setup_error",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def export_data_to_sheets(self, user_id: int) -> bool:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user or not user.spreadsheet_id:
                logger.warning(
                    "Пользователь попытался экспортировать данные без настроенного Google Sheets",
                    event_type="google_sheets_export_no_config",
                    user_id=user_id,
                )
                raise ValueError("Google Sheets не настроен для этого пользователя.")

            logger.info(
                "Начало экспорта данных в Google Sheets",
                event_type="google_sheets_export_started",
                user_id=user_id,
                spreadsheet_id=user.spreadsheet_id,
            )

            # Экспорт тренажёров (upsert)
            machines = await self.machine_repository.get_user_machines(
                user_id, include_archived=True
            )
            if machines:
                machine_data = [
                    {
                        "ID": m.id,
                        "Название": m.name,
                        "Фото ID": m.photo_file_id,
                        "Архивирован": "Да" if m.is_archived else "Нет",
                        "Мышцы": (
                            ", ".join([mu.name for mu in m.muscles])
                            if m.muscles
                            else ""
                        ),
                    }
                    for m in machines
                ]
                machines_df = pd.DataFrame(machine_data)
                self.google_sheets_client.upsert_dataframe(
                    user.spreadsheet_id, "Machines", machines_df, "ID"
                )
                logger.info(
                    "Пользователь успешно экспортировал тренажёры в Google Sheets",
                    event_type="google_sheets_machines_exported",
                    user_id=user_id,
                    spreadsheet_id=user.spreadsheet_id,
                    machines_count=len(machines),
                )

            # Экспорт подходов (append) - Заглушка
            logger.info(
                "Экспорт подходов ожидает реализации",
                event_type="google_sheets_sets_export_pending",
                user_id=user_id,
            )

            return True
        except Exception as e:
            logger.error(
                "Ошибка при экспорте данных в Google Sheets",
                event_type="google_sheets_export_error",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise
