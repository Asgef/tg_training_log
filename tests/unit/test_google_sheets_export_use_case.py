"""Unit тесты для GoogleSheetsExportUseCase."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from src.application.use_cases.google_sheets_export import GoogleSheetsExportUseCase
from src.domain.models import User, Machine


@pytest.mark.unit
class TestGoogleSheetsExportUseCase:
    """Тесты для GoogleSheetsExportUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Создаёт мок UserRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_machine_repository(self):
        """Создаёт мок MachineRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_set_entry_repository(self):
        """Создаёт мок SetEntryRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_google_sheets_client(self):
        """Создаёт мок GoogleSheetsClient."""
        return MagicMock()

    @pytest.fixture
    def google_sheets_export_use_case(
        self,
        mock_user_repository,
        mock_machine_repository,
        mock_set_entry_repository,
        mock_google_sheets_client,
    ):
        """Создаёт экземпляр GoogleSheetsExportUseCase с моками."""
        return GoogleSheetsExportUseCase(
            user_repository=mock_user_repository,
            machine_repository=mock_machine_repository,
            set_entry_repository=mock_set_entry_repository,
            google_sheets_client=mock_google_sheets_client,
        )

    @pytest.fixture
    def test_user(self):
        """Создаёт тестового пользователя."""
        now = datetime.now(timezone.utc)
        return User(
            id=123456789,
            telegram_username="testuser",
            telegram_firstname="Test",
            telegram_lastname="User",
            is_registered=True,
            spreadsheet_id="test_spreadsheet_id",
            google_sheet_url="https://docs.google.com/spreadsheets/d/test_spreadsheet_id/edit",
            created_at=now,
            updated_at=now,
            timezone="Europe/Berlin",
        )

    @pytest.fixture
    def test_machine(self):
        """Создаёт тестовый тренажёр."""
        now = datetime.now(timezone.utc)
        return Machine(
            id=1,
            user_id=123456789,
            name="Test Machine",
            is_archived=False,
            created_at=now,
            updated_at=now,
        )

    async def test_setup_google_sheets_config_success(
        self,
        google_sheets_export_use_case,
        mock_user_repository,
    ):
        """Тест успешной настройки конфигурации Google Sheets."""
        # Настраиваем моки
        mock_user_repository.save_google_sheet_config.return_value = None

        # Вызываем метод
        result = await google_sheets_export_use_case.setup_google_sheets_config(
            user_id=123456789,
            sheet_url="https://docs.google.com/spreadsheets/d/test_id/edit",
        )

        # Проверяем результат
        assert result is True
        mock_user_repository.save_google_sheet_config.assert_called_once_with(
            123456789, "https://docs.google.com/spreadsheets/d/test_id/edit", "test_id"
        )

    async def test_setup_google_sheets_config_invalid_url(
        self,
        google_sheets_export_use_case,
    ):
        """Тест настройки конфигурации с неверным URL."""
        # Вызываем метод с неверным URL и ожидаем ValueError
        with pytest.raises(ValueError, match="не является валидным"):
            await google_sheets_export_use_case.setup_google_sheets_config(
                user_id=123456789,
                sheet_url="https://example.com/not-google-sheets",
            )

    async def test_setup_google_sheets_config_missing_id(
        self,
        google_sheets_export_use_case,
    ):
        """Тест настройки конфигурации с URL без ID таблицы."""
        # Вызываем метод с URL без "d" в пути и ожидаем ValueError
        with pytest.raises(ValueError, match="Could not extract"):
            await google_sheets_export_use_case.setup_google_sheets_config(
                user_id=123456789,
                sheet_url="https://docs.google.com/spreadsheets/",
            )

    async def test_export_data_to_sheets_success(
        self,
        google_sheets_export_use_case,
        mock_user_repository,
        mock_machine_repository,
        mock_google_sheets_client,
        test_user,
        test_machine,
    ):
        """Тест успешного экспорта данных в Google Sheets."""
        # Настраиваем моки
        mock_user_repository.get_by_id.return_value = test_user
        mock_machine_repository.get_user_machines.return_value = [test_machine]
        mock_google_sheets_client.upsert_dataframe.return_value = None

        # Вызываем метод
        result = await google_sheets_export_use_case.export_data_to_sheets(
            user_id=123456789
        )

        # Проверяем результат
        assert result is True
        mock_user_repository.get_by_id.assert_called_once_with(123456789)
        mock_machine_repository.get_user_machines.assert_called_once_with(
            123456789, include_archived=True
        )
        mock_google_sheets_client.upsert_dataframe.assert_called_once()

    async def test_export_data_to_sheets_user_not_found(
        self,
        google_sheets_export_use_case,
        mock_user_repository,
    ):
        """Тест экспорта данных для несуществующего пользователя."""
        # Настраиваем моки: пользователь не найден
        mock_user_repository.get_by_id.return_value = None

        # Вызываем метод и ожидаем ValueError
        with pytest.raises(ValueError, match="не настроен"):
            await google_sheets_export_use_case.export_data_to_sheets(user_id=123456789)

    async def test_export_data_to_sheets_no_spreadsheet_id(
        self,
        google_sheets_export_use_case,
        mock_user_repository,
    ):
        """Тест экспорта данных для пользователя без настроенного Google Sheets."""
        # Настраиваем моки: пользователь без spreadsheet_id
        now = datetime.now(timezone.utc)
        user_without_sheet = User(
            id=123456789,
            telegram_username="testuser",
            is_registered=True,
            spreadsheet_id=None,
            google_sheet_url=None,
            created_at=now,
            updated_at=now,
            timezone="Europe/Berlin",
        )
        mock_user_repository.get_by_id.return_value = user_without_sheet

        # Вызываем метод и ожидаем ValueError
        with pytest.raises(ValueError, match="не настроен"):
            await google_sheets_export_use_case.export_data_to_sheets(user_id=123456789)

    async def test_export_data_to_sheets_no_machines(
        self,
        google_sheets_export_use_case,
        mock_user_repository,
        mock_machine_repository,
        mock_google_sheets_client,
        test_user,
    ):
        """Тест экспорта данных, когда нет тренажёров."""
        # Настраиваем моки: нет тренажёров
        mock_user_repository.get_by_id.return_value = test_user
        mock_machine_repository.get_user_machines.return_value = []

        # Вызываем метод
        result = await google_sheets_export_use_case.export_data_to_sheets(
            user_id=123456789
        )

        # Проверяем результат
        assert result is True
        # upsert_dataframe не должен вызываться, если нет тренажёров
        mock_google_sheets_client.upsert_dataframe.assert_not_called()
