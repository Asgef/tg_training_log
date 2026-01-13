import logging
from urllib.parse import urlparse

import pandas as pd

from src.application.repositories import (
    IUserRepository,
    IMachineRepository,
    ISetEntryRepository,
)
from src.application.use_cases import IGoogleSheetsExportUseCase
from src.infrastructure.services.google_sheets_client import GoogleSheetsClient

logger = logging.getLogger(__name__)


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
                    f"User {user_id} provided invalid Google Sheets URL: {sheet_url}"
                )
                raise ValueError("Provided URL is not a valid Google Sheets URL.")

            path_parts = parsed_url.path.split("/")
            if "d" in path_parts:
                try:
                    spreadsheet_id = path_parts[path_parts.index("d") + 1]
                except IndexError:
                    logger.warning(
                        f"User {user_id} provided URL without detectable spreadsheet ID: {sheet_url}"
                    )
                    raise ValueError("Could not extract spreadsheet ID from the URL.")
            else:
                logger.warning(
                    f"User {user_id} provided URL without detectable spreadsheet ID: {sheet_url}"
                )
                raise ValueError("Could not extract spreadsheet ID from the URL.")

            await self.user_repository.save_google_sheet_config(
                user_id, sheet_url, spreadsheet_id
            )
            logger.info(
                f"User {user_id} successfully configured Google Sheets with ID: {spreadsheet_id}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error setting up Google Sheets config for user {user_id}: {e}"
            )
            raise

    async def export_data_to_sheets(self, user_id: int) -> bool:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user or not user.spreadsheet_id:
                logger.warning(
                    f"User {user_id} tried to export data without configured Google Sheets."
                )
                raise ValueError("Google Sheets not configured for this user.")

            # Export Machines (upsert)
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
                    f"User {user_id} successfully exported {len(machines)} machines to Google Sheet {user.spreadsheet_id}."
                )

            # Export Set Entries (append) - Placeholder
            logger.info(
                f"Set entries export for user {user_id} is pending implementation."
            )

            return True
        except Exception as e:
            logger.error(
                f"Error exporting data to Google Sheets for user {user_id}: {e}"
            )
            raise
