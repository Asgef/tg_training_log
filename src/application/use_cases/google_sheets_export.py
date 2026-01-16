import structlog
from urllib.parse import urlparse

from src.application.repositories import (
    IUserRepository,
    IMachineRepository,
    ISetEntryRepository,
    IMuscleRepository,
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
        muscle_repository: IMuscleRepository,
        google_sheets_client: GoogleSheetsClient,
    ):
        self.user_repository = user_repository
        self.machine_repository = machine_repository
        self.set_entry_repository = set_entry_repository
        self.muscle_repository = muscle_repository
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

    async def export_data_to_sheets(self, user_id: int) -> dict:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user or not user.spreadsheet_id:
                logger.warning(
                    "Пользователь попытался экспортировать данные без настроенного Google Sheets",
                    event_type="google_sheets_export_no_config",
                    user_id=user_id,
                )
                raise ValueError("Google Sheets не настроен для этого пользователя.")

            if self.google_sheets_client is None:
                raise RuntimeError("Google Sheets клиент не инициализирован.")

            logger.info(
                "Начало экспорта данных в Google Sheets",
                event_type="google_sheets_export_started",
                user_id=user_id,
                spreadsheet_id=user.spreadsheet_id,
            )

            # Справочники: REF_MACHINES, REF_ZONES, REF_MUSCLES, REF_ZONE_MUSCLES
            machines = await self.machine_repository.get_user_machines(
                user_id, include_archived=True
            )
            machine_rows = [
                [
                    m.id,
                    m.name,
                    "TRUE" if m.is_archived else "FALSE",
                    ", ".join(sorted({z.name for z in m.zones})) if m.zones else "",
                    ", ".join(sorted({mu.name for mu in m.muscles})) if m.muscles else "",
                    m.updated_at.isoformat() if m.updated_at else "",
                ]
                for m in machines
            ]

            zones = await self.muscle_repository.get_all_muscle_zones()
            zone_rows = [
                [z.id, z.name, z.updated_at.isoformat() if z.updated_at else ""]
                for z in zones
            ]

            muscles = await self.muscle_repository.get_all_muscles()
            muscle_rows = [
                [m.id, m.name, m.updated_at.isoformat() if m.updated_at else ""]
                for m in muscles
            ]

            zone_muscle_links = await self.muscle_repository.get_zone_muscle_links()
            zone_muscle_rows = [
                [
                    link["zone_id"],
                    link["zone_name"],
                    link["muscle_id"],
                    link["muscle_name"],
                ]
                for link in zone_muscle_links
            ]

            self.google_sheets_client.replace_worksheet_data(
                user.spreadsheet_id,
                "REF_MACHINES",
                "Справочник тренажёров",
                [
                    "ID тренажёра",
                    "Название",
                    "Архивирован",
                    "Зоны (текущие)",
                    "Мышцы (текущие)",
                    "Обновлено",
                ],
                [
                    "machine_id",
                    "machine_name",
                    "is_archived",
                    "zone_names_current",
                    "muscle_names_current",
                    "updated_at",
                ],
                machine_rows,
            )
            self.google_sheets_client.replace_worksheet_data(
                user.spreadsheet_id,
                "REF_ZONES",
                "Справочник зон",
                ["ID зоны", "Название зоны", "Обновлено"],
                ["zone_id", "zone_name", "updated_at"],
                zone_rows,
            )
            self.google_sheets_client.replace_worksheet_data(
                user.spreadsheet_id,
                "REF_MUSCLES",
                "Справочник мышц",
                ["ID мышцы", "Название мышцы", "Обновлено"],
                ["muscle_id", "muscle_name", "updated_at"],
                muscle_rows,
            )
            self.google_sheets_client.replace_worksheet_data(
                user.spreadsheet_id,
                "REF_ZONE_MUSCLES",
                "Связь зон и мышц",
                ["ID зоны", "Название зоны", "ID мышцы", "Название мышцы"],
                ["zone_id", "zone_name", "muscle_id", "muscle_name"],
                zone_muscle_rows,
            )

            # LOG_SETS и LOG_MUSCLES (append-only)
            min_set_id = user.last_exported_set_id
            set_rows_raw = await self.set_entry_repository.get_sets_for_export(
                user_id, min_set_id
            )
            muscle_rows_raw = await self.set_entry_repository.get_set_entry_muscles_for_export(
                user_id, min_set_id
            )
            zone_snapshot_rows = (
                await self.set_entry_repository.get_set_entry_zone_snapshots_for_export(
                    user_id, min_set_id
                )
            )

            zone_snapshot_map: dict[int, list[str]] = {}
            for row in zone_snapshot_rows:
                zone_snapshot_map.setdefault(row["set_id"], []).append(row["zone_name"])

            log_sets_rows = []
            for row in set_rows_raw:
                performed_at = row["performed_at"]
                date_str = performed_at.date().isoformat() if performed_at else ""
                time_str = performed_at.time().isoformat(timespec="seconds") if performed_at else ""
                weight = float(row["weight"])
                reps = int(row["reps"])
                log_sets_rows.append(
                    [
                        row["set_id"],
                        performed_at.isoformat() if performed_at else "",
                        date_str,
                        time_str,
                        row["session_id"],
                        row["machine_id"],
                        row["machine_name"],
                        weight,
                        reps,
                        "TRUE" if row["is_failure"] else "FALSE",
                        weight * reps,
                    ]
                )

            log_muscles_rows = []
            for row in muscle_rows_raw:
                performed_at = row["performed_at"]
                date_str = performed_at.date().isoformat() if performed_at else ""
                time_str = performed_at.time().isoformat(timespec="seconds") if performed_at else ""
                weight = float(row["weight"])
                reps = int(row["reps"])
                zones_snapshot = zone_snapshot_map.get(row["set_id"], [])
                log_muscles_rows.append(
                    [
                        row["set_id"],
                        performed_at.isoformat() if performed_at else "",
                        date_str,
                        time_str,
                        row["session_id"],
                        row["machine_id"],
                        row["machine_name"],
                        row["muscle_id"],
                        row["muscle_name"],
                        weight,
                        reps,
                        "TRUE" if row["is_failure"] else "FALSE",
                        weight * reps,
                        ", ".join(sorted(set(zones_snapshot))) if zones_snapshot else "",
                    ]
                )

            if log_sets_rows:
                self.google_sheets_client.append_data(
                    user.spreadsheet_id,
                    "LOG_SETS",
                    "Журнал подходов",
                    [
                        "ID подхода",
                        "Время выполнения",
                        "Дата",
                        "Время",
                        "ID сессии",
                        "ID тренажёра",
                        "Название тренажёра",
                        "Вес, кг",
                        "Повторения",
                        "Отказ",
                        "Объём",
                    ],
                    [
                        "set_id",
                        "performed_at",
                        "date",
                        "time",
                        "session_id",
                        "machine_id",
                        "machine_name",
                        "weight_kg",
                        "reps",
                        "is_failure",
                        "volume",
                    ],
                    log_sets_rows,
                )

            if log_muscles_rows:
                self.google_sheets_client.append_data(
                    user.spreadsheet_id,
                    "LOG_MUSCLES",
                    "Нагрузка по мышцам",
                    [
                        "ID подхода",
                        "Время выполнения",
                        "Дата",
                        "Время",
                        "ID сессии",
                        "ID тренажёра",
                        "Название тренажёра",
                        "ID мышцы",
                        "Название мышцы",
                        "Вес, кг",
                        "Повторения",
                        "Отказ",
                        "Объём",
                        "Зоны (снимок)",
                    ],
                    [
                        "set_id",
                        "performed_at",
                        "date",
                        "time",
                        "session_id",
                        "machine_id",
                        "machine_name",
                        "muscle_id",
                        "muscle_name",
                        "weight_kg",
                        "reps",
                        "is_failure",
                        "volume",
                        "zone_names_snapshot",
                    ],
                    log_muscles_rows,
                )

            if log_sets_rows:
                user.last_exported_set_id = max(
                    row["set_id"] for row in set_rows_raw
                )
                await self.user_repository.update(user)

            return {
                "sets_added": len(log_sets_rows),
                "muscles_added": len(log_muscles_rows),
            }
        except Exception as e:
            logger.error(
                "Ошибка при экспорте данных в Google Sheets",
                event_type="google_sheets_export_error",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise
