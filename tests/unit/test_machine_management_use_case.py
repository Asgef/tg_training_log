"""Unit тесты для MachineManagementUseCase."""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from src.application.use_cases.machine_management import MachineManagementUseCase
from src.domain.models import Machine, Muscle, MuscleZone


@pytest.mark.unit
class TestMachineManagementUseCase:
    """Тесты для MachineManagementUseCase."""

    @pytest.fixture
    def mock_machine_repository(self):
        """Создаёт мок MachineRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_muscle_repository(self):
        """Создаёт мок MuscleRepository."""
        return AsyncMock()

    @pytest.fixture
    def machine_management_use_case(
        self, mock_machine_repository, mock_muscle_repository
    ):
        """Создаёт экземпляр MachineManagementUseCase с моками репозиториев."""
        return MachineManagementUseCase(
            machine_repository=mock_machine_repository,
            muscle_repository=mock_muscle_repository,
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

    @pytest.fixture
    def test_muscle(self):
        """Создаёт тестовую мышцу."""
        now = datetime.now(timezone.utc)
        return Muscle(
            id=1,
            name="Test Muscle",
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    def test_muscle_zone(self):
        """Создаёт тестовую мышечную зону."""
        now = datetime.now(timezone.utc)
        return MuscleZone(
            id=1,
            name="Test Zone",
            created_at=now,
            updated_at=now,
        )

    async def test_add_machine_success(
        self,
        machine_management_use_case,
        mock_machine_repository,
        mock_muscle_repository,
        test_machine,
        test_muscle,
        test_muscle_zone,
    ):
        """Тест успешного добавления тренажёра."""
        # Настраиваем моки
        mock_machine_repository.get_user_machine_by_name.return_value = None
        mock_muscle_repository.get_muscle_zones_by_ids.return_value = [test_muscle_zone]
        mock_muscle_repository.get_muscles_by_ids.return_value = [test_muscle]
        mock_machine_repository.add_machine_with_tags.return_value = test_machine

        # Вызываем метод
        result = await machine_management_use_case.add_machine(
            user_id=123456789,
            name="Test Machine",
            photo_file_id=None,
            zone_ids=[1],
            muscle_ids=[1],
        )

        # Проверяем результат
        assert result is not None
        assert result.id == 1
        mock_machine_repository.get_user_machine_by_name.assert_called_once_with(
            123456789, "Test Machine"
        )
        mock_muscle_repository.get_muscle_zones_by_ids.assert_called_once_with([1])
        mock_muscle_repository.get_muscles_by_ids.assert_called_once_with([1])
        mock_machine_repository.add_machine_with_tags.assert_called_once()

    async def test_add_machine_duplicate_name(
        self,
        machine_management_use_case,
        mock_machine_repository,
        test_machine,
    ):
        """Тест добавления тренажёра с дублирующимся именем."""
        # Настраиваем моки: тренажёр с таким именем уже существует
        mock_machine_repository.get_user_machine_by_name.return_value = test_machine

        # Вызываем метод и ожидаем ValueError
        with pytest.raises(ValueError, match="уже существует"):
            await machine_management_use_case.add_machine(
                user_id=123456789,
                name="Test Machine",
                photo_file_id=None,
                zone_ids=[],
                muscle_ids=[],
            )

    async def test_add_machine_invalid_muscle_ids(
        self,
        machine_management_use_case,
        mock_machine_repository,
        mock_muscle_repository,
        test_muscle,
    ):
        """Тест добавления тренажёра с неверными ID мышц."""
        # Настраиваем моки
        mock_machine_repository.get_user_machine_by_name.return_value = None
        mock_muscle_repository.get_muscle_zones_by_ids.return_value = []
        # Возвращаем меньше мышц, чем запрошено
        mock_muscle_repository.get_muscles_by_ids.return_value = [test_muscle]

        # Вызываем метод и ожидаем ValueError
        with pytest.raises(ValueError, match="не существуют"):
            await machine_management_use_case.add_machine(
                user_id=123456789,
                name="Test Machine",
                photo_file_id=None,
                zone_ids=[],
                muscle_ids=[1, 2],  # Запрашиваем 2, но получаем только 1
            )

    async def test_get_user_machines_success(
        self,
        machine_management_use_case,
        mock_machine_repository,
        test_machine,
    ):
        """Тест успешного получения тренажёров пользователя."""
        # Настраиваем моки
        mock_machine_repository.get_user_machines.return_value = [test_machine]

        # Вызываем метод
        result = await machine_management_use_case.get_user_machines(user_id=123456789)

        # Проверяем результат
        assert len(result) == 1
        assert result[0].id == 1
        mock_machine_repository.get_user_machines.assert_called_once_with(
            123456789, include_archived=False
        )

    async def test_get_user_machines_empty(
        self,
        machine_management_use_case,
        mock_machine_repository,
    ):
        """Тест получения тренажёров, когда их нет."""
        # Настраиваем моки: нет тренажёров
        mock_machine_repository.get_user_machines.return_value = []

        # Вызываем метод
        result = await machine_management_use_case.get_user_machines(user_id=123456789)

        # Проверяем результат
        assert len(result) == 0

    async def test_get_machine_details_success(
        self,
        machine_management_use_case,
        mock_machine_repository,
        test_machine,
    ):
        """Тест успешного получения деталей тренажёра."""
        # Настраиваем моки
        mock_machine_repository.get_by_id.return_value = test_machine

        # Вызываем метод
        result = await machine_management_use_case.get_machine_details(
            user_id=123456789, machine_id=1
        )

        # Проверяем результат
        assert result is not None
        assert result.id == 1
        mock_machine_repository.get_by_id.assert_called_once_with(1)

    async def test_get_machine_details_not_found(
        self,
        machine_management_use_case,
        mock_machine_repository,
    ):
        """Тест получения несуществующего тренажёра."""
        # Настраиваем моки: тренажёр не найден
        mock_machine_repository.get_by_id.return_value = None

        # Вызываем метод
        result = await machine_management_use_case.get_machine_details(
            user_id=123456789, machine_id=999
        )

        # Проверяем результат
        assert result is None

    async def test_get_machine_details_wrong_owner(
        self,
        machine_management_use_case,
        mock_machine_repository,
    ):
        """Тест получения тренажёра другого пользователя."""
        # Настраиваем моки: тренажёр принадлежит другому пользователю
        now = datetime.now(timezone.utc)
        other_machine = Machine(
            id=1,
            user_id=999999999,  # Другой пользователь
            name="Other Machine",
            is_archived=False,
            created_at=now,
            updated_at=now,
        )
        mock_machine_repository.get_by_id.return_value = other_machine

        # Вызываем метод
        result = await machine_management_use_case.get_machine_details(
            user_id=123456789, machine_id=1
        )

        # Проверяем результат
        assert result is None

    async def test_update_machine_success(
        self,
        machine_management_use_case,
        mock_machine_repository,
        test_machine,
    ):
        """Тест успешного обновления тренажёра."""
        # Настраиваем моки
        now = datetime.now(timezone.utc)
        updated_machine = Machine(
            id=1,
            user_id=123456789,
            name="Updated Machine",
            is_archived=False,
            created_at=now,
            updated_at=now,
        )
        mock_machine_repository.get_by_id.return_value = test_machine
        mock_machine_repository.get_user_machine_by_name.return_value = None
        mock_machine_repository.update.return_value = updated_machine

        # Вызываем метод
        result = await machine_management_use_case.update_machine(
            user_id=123456789,
            machine_id=1,
            name="Updated Machine",
            photo_file_id=None,
            zone_ids=None,
            muscle_ids=None,
            is_archived=None,
        )

        # Проверяем результат
        assert result is not None
        assert result.name == "Updated Machine"
        mock_machine_repository.update.assert_called_once()

    async def test_update_machine_duplicate_name(
        self,
        machine_management_use_case,
        mock_machine_repository,
        test_machine,
    ):
        """Тест обновления тренажёра с дублирующимся именем."""
        # Настраиваем моки
        now = datetime.now(timezone.utc)
        existing_machine = Machine(
            id=2,  # Другой тренажёр
            user_id=123456789,
            name="Existing Machine",
            is_archived=False,
            created_at=now,
            updated_at=now,
        )
        mock_machine_repository.get_by_id.return_value = test_machine
        mock_machine_repository.get_user_machine_by_name.return_value = existing_machine

        # Вызываем метод и ожидаем ValueError
        with pytest.raises(ValueError, match="уже существует"):
            await machine_management_use_case.update_machine(
                user_id=123456789,
                machine_id=1,
                name="Existing Machine",
                photo_file_id=None,
                zone_ids=None,
                muscle_ids=None,
                is_archived=None,
            )

    async def test_archive_machine_success(
        self,
        machine_management_use_case,
        mock_machine_repository,
        test_machine,
    ):
        """Тест успешной архивации тренажёра."""
        # Настраиваем моки
        archived_machine = Machine(
            id=1,
            user_id=123456789,
            name="Test Machine",
            is_archived=True,
        )
        mock_machine_repository.get_by_id.return_value = test_machine
        mock_machine_repository.update.return_value = archived_machine

        # Вызываем метод
        result = await machine_management_use_case.archive_machine(
            user_id=123456789, machine_id=1
        )

        # Проверяем результат
        assert result is True
        updated_machine = mock_machine_repository.update.call_args[0][0]
        assert updated_machine.is_archived is True

    async def test_archive_machine_already_archived(
        self,
        machine_management_use_case,
        mock_machine_repository,
    ):
        """Тест архивации уже архивированного тренажёра."""
        # Настраиваем моки: тренажёр уже архивирован
        archived_machine = Machine(
            id=1,
            user_id=123456789,
            name="Test Machine",
            is_archived=True,
        )
        mock_machine_repository.get_by_id.return_value = archived_machine

        # Вызываем метод
        result = await machine_management_use_case.archive_machine(
            user_id=123456789, machine_id=1
        )

        # Проверяем результат
        assert result is False
        mock_machine_repository.update.assert_not_called()

    async def test_get_all_muscle_zones_success(
        self,
        machine_management_use_case,
        mock_muscle_repository,
        test_muscle_zone,
    ):
        """Тест успешного получения всех зон."""
        # Настраиваем моки
        mock_muscle_repository.get_all_muscle_zones.return_value = [test_muscle_zone]

        # Вызываем метод
        result = await machine_management_use_case.get_all_muscle_zones()

        # Проверяем результат
        assert len(result) == 1
        assert result[0].id == 1
        mock_muscle_repository.get_all_muscle_zones.assert_called_once()

    async def test_get_muscles_by_zone_id_success(
        self,
        machine_management_use_case,
        mock_muscle_repository,
        test_muscle,
    ):
        """Тест успешного получения мышц по ID зоны."""
        # Настраиваем моки
        mock_muscle_repository.get_muscles_by_zone_id.return_value = [test_muscle]

        # Вызываем метод
        result = await machine_management_use_case.get_muscles_by_zone_id(zone_id=1)

        # Проверяем результат
        assert len(result) == 1
        assert result[0].id == 1
        mock_muscle_repository.get_muscles_by_zone_id.assert_called_once_with(1)

    async def test_get_muscle_zone_by_id_success(
        self,
        machine_management_use_case,
        mock_muscle_repository,
        test_muscle_zone,
    ):
        """Тест успешного получения зоны по ID."""
        # Настраиваем моки
        mock_muscle_repository.get_muscle_zone_by_id.return_value = test_muscle_zone

        # Вызываем метод
        result = await machine_management_use_case.get_muscle_zone_by_id(zone_id=1)

        # Проверяем результат
        assert result is not None
        assert result.id == 1
        mock_muscle_repository.get_muscle_zone_by_id.assert_called_once_with(1)

    async def test_get_muscle_zone_by_id_not_found(
        self,
        machine_management_use_case,
        mock_muscle_repository,
    ):
        """Тест получения несуществующей зоны."""
        # Настраиваем моки: группа не найдена
        mock_muscle_repository.get_muscle_zone_by_id.return_value = None

        # Вызываем метод
        result = await machine_management_use_case.get_muscle_zone_by_id(zone_id=999)

        # Проверяем результат
        assert result is None
