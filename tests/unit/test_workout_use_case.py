"""Unit тесты для WorkoutUseCase."""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from src.application.use_cases.workout import WorkoutUseCase
from src.domain.models import WorkoutSession, SetEntry, Machine


@pytest.mark.unit
class TestWorkoutUseCase:
    """Тесты для WorkoutUseCase."""

    @pytest.fixture
    def mock_workout_session_repository(self):
        """Создаёт мок WorkoutSessionRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_set_entry_repository(self):
        """Создаёт мок SetEntryRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_machine_repository(self):
        """Создаёт мок MachineRepository."""
        return AsyncMock()

    @pytest.fixture
    def workout_use_case(
        self,
        mock_workout_session_repository,
        mock_set_entry_repository,
        mock_machine_repository,
    ):
        """Создаёт экземпляр WorkoutUseCase с моками репозиториев."""
        return WorkoutUseCase(
            workout_session_repository=mock_workout_session_repository,
            set_entry_repository=mock_set_entry_repository,
            machine_repository=mock_machine_repository,
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
    def test_workout_session(self):
        """Создаёт тестовую сессию тренировки."""
        now = datetime.now(timezone.utc)
        return WorkoutSession(
            id=1,
            user_id=123456789,
            started_at=now,
            ended_at=None,
            created_at=now,
            updated_at=now,
        )

    async def test_start_new_workout_success(
        self,
        workout_use_case,
        mock_machine_repository,
        mock_workout_session_repository,
        test_machine,
        test_workout_session,
    ):
        """Тест успешного начала новой тренировки."""
        # Настраиваем моки
        mock_machine_repository.get_user_machines.return_value = [test_machine]
        mock_workout_session_repository.get_active_session_for_user.return_value = None
        mock_workout_session_repository.start_session.return_value = test_workout_session

        # Вызываем метод
        result = await workout_use_case.start_new_workout(user_id=123456789)

        # Проверяем результат
        assert result is not None
        assert result.id == 1
        mock_machine_repository.get_user_machines.assert_called_once_with(
            123456789, include_archived=False
        )
        mock_workout_session_repository.get_active_session_for_user.assert_called_once_with(
            123456789
        )
        mock_workout_session_repository.start_session.assert_called_once_with(123456789)

    async def test_start_new_workout_no_machines(
        self,
        workout_use_case,
        mock_machine_repository,
        mock_workout_session_repository,
    ):
        """Тест начала тренировки без тренажёров."""
        # Настраиваем моки: нет тренажёров
        mock_machine_repository.get_user_machines.return_value = []

        # Вызываем метод и ожидаем ValueError
        with pytest.raises(ValueError, match="У вас нет тренажеров"):
            await workout_use_case.start_new_workout(user_id=123456789)

        mock_machine_repository.get_user_machines.assert_called_once_with(
            123456789, include_archived=False
        )
        mock_workout_session_repository.start_session.assert_not_called()

    async def test_start_new_workout_active_session_exists(
        self,
        workout_use_case,
        mock_machine_repository,
        mock_workout_session_repository,
        test_machine,
        test_workout_session,
    ):
        """Тест начала тренировки при существующей активной сессии."""
        # Настраиваем моки
        mock_machine_repository.get_user_machines.return_value = [test_machine]
        mock_workout_session_repository.get_active_session_for_user.return_value = (
            test_workout_session
        )

        # Вызываем метод
        result = await workout_use_case.start_new_workout(user_id=123456789)

        # Проверяем результат
        assert result is None
        mock_workout_session_repository.start_session.assert_not_called()

    async def test_end_current_workout_success(
        self,
        workout_use_case,
        mock_workout_session_repository,
        test_workout_session,
    ):
        """Тест успешного завершения тренировки."""
        # Настраиваем моки
        mock_workout_session_repository.get_active_session_for_user.return_value = (
            test_workout_session
        )
        mock_workout_session_repository.end_session.return_value = None
        mock_workout_session_repository.get_by_id.return_value = test_workout_session

        # Вызываем метод
        result = await workout_use_case.end_current_workout(user_id=123456789)

        # Проверяем результат
        assert result is not None
        assert result.id == 1
        mock_workout_session_repository.get_active_session_for_user.assert_called_once_with(
            123456789
        )
        mock_workout_session_repository.end_session.assert_called_once_with(1)
        mock_workout_session_repository.get_by_id.assert_called_once_with(1)

    async def test_end_current_workout_no_active_session(
        self,
        workout_use_case,
        mock_workout_session_repository,
    ):
        """Тест завершения тренировки без активной сессии."""
        # Настраиваем моки: нет активной сессии
        mock_workout_session_repository.get_active_session_for_user.return_value = None

        # Вызываем метод
        result = await workout_use_case.end_current_workout(user_id=123456789)

        # Проверяем результат
        assert result is None
        mock_workout_session_repository.end_session.assert_not_called()

    async def test_record_set_success(
        self,
        workout_use_case,
        mock_workout_session_repository,
        mock_machine_repository,
        mock_set_entry_repository,
        test_workout_session,
        test_machine,
    ):
        """Тест успешной записи подхода."""
        # Настраиваем моки
        mock_workout_session_repository.get_active_session_for_user.return_value = (
            test_workout_session
        )
        mock_machine_repository.get_by_id.return_value = test_machine
        # add_set_entry модифицирует объект in-place, поэтому используем side_effect
        now = datetime.now(timezone.utc)
        async def add_set_entry_side_effect(entry):
            entry.id = 1
            entry.created_at = now
            entry.updated_at = now
            return entry
        mock_set_entry_repository.add_set_entry.side_effect = add_set_entry_side_effect

        # Вызываем метод
        result = await workout_use_case.record_set(
            user_id=123456789,
            machine_id=1,
            weight=100.0,
            reps=10,
            failure=False,
        )

        # Проверяем результат
        assert result is not None
        assert result.weight == 100.0
        assert result.reps == 10
        mock_workout_session_repository.get_active_session_for_user.assert_called_once_with(
            123456789
        )
        mock_machine_repository.get_by_id.assert_called_once_with(1)
        mock_set_entry_repository.add_set_entry.assert_called_once()

    async def test_record_set_no_active_session(
        self,
        workout_use_case,
        mock_workout_session_repository,
    ):
        """Тест записи подхода без активной сессии."""
        # Настраиваем моки: нет активной сессии
        mock_workout_session_repository.get_active_session_for_user.return_value = None

        # Вызываем метод
        result = await workout_use_case.record_set(
            user_id=123456789,
            machine_id=1,
            weight=100.0,
            reps=10,
            failure=False,
        )

        # Проверяем результат
        assert result is None

    async def test_record_set_machine_not_found(
        self,
        workout_use_case,
        mock_workout_session_repository,
        mock_machine_repository,
        test_workout_session,
    ):
        """Тест записи подхода на несуществующий тренажёр."""
        # Настраиваем моки
        mock_workout_session_repository.get_active_session_for_user.return_value = (
            test_workout_session
        )
        mock_machine_repository.get_by_id.return_value = None

        # Вызываем метод и ожидаем ValueError
        with pytest.raises(ValueError, match="не найден"):
            await workout_use_case.record_set(
                user_id=123456789,
                machine_id=999,
                weight=100.0,
                reps=10,
                failure=False,
            )

    async def test_record_set_machine_belongs_to_other_user(
        self,
        workout_use_case,
        mock_workout_session_repository,
        mock_machine_repository,
        test_workout_session,
    ):
        """Тест записи подхода на тренажёр другого пользователя."""
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
        mock_workout_session_repository.get_active_session_for_user.return_value = (
            test_workout_session
        )
        mock_machine_repository.get_by_id.return_value = other_machine

        # Вызываем метод и ожидаем ValueError
        with pytest.raises(ValueError, match="не принадлежит вам"):
            await workout_use_case.record_set(
                user_id=123456789,
                machine_id=1,
                weight=100.0,
                reps=10,
                failure=False,
            )

    async def test_record_set_machine_archived(
        self,
        workout_use_case,
        mock_workout_session_repository,
        mock_machine_repository,
        test_workout_session,
    ):
        """Тест записи подхода на архивированный тренажёр."""
        # Настраиваем моки: тренажёр архивирован
        now = datetime.now(timezone.utc)
        archived_machine = Machine(
            id=1,
            user_id=123456789,
            name="Archived Machine",
            is_archived=True,
            created_at=now,
            updated_at=now,
        )
        mock_workout_session_repository.get_active_session_for_user.return_value = (
            test_workout_session
        )
        mock_machine_repository.get_by_id.return_value = archived_machine

        # Вызываем метод и ожидаем ValueError
        with pytest.raises(ValueError, match="архивирован"):
            await workout_use_case.record_set(
                user_id=123456789,
                machine_id=1,
                weight=100.0,
                reps=10,
                failure=False,
            )

    async def test_get_active_workout_session_success(
        self,
        workout_use_case,
        mock_workout_session_repository,
        test_workout_session,
    ):
        """Тест успешного получения активной сессии тренировки."""
        # Настраиваем моки
        mock_workout_session_repository.get_active_session_for_user.return_value = (
            test_workout_session
        )

        # Вызываем метод
        result = await workout_use_case.get_active_workout_session(user_id=123456789)

        # Проверяем результат
        assert result is not None
        assert result.id == 1
        mock_workout_session_repository.get_active_session_for_user.assert_called_once_with(
            123456789
        )

    async def test_get_active_workout_session_not_found(
        self,
        workout_use_case,
        mock_workout_session_repository,
    ):
        """Тест получения активной сессии, когда её нет."""
        # Настраиваем моки: нет активной сессии
        mock_workout_session_repository.get_active_session_for_user.return_value = None

        # Вызываем метод
        result = await workout_use_case.get_active_workout_session(user_id=123456789)

        # Проверяем результат
        assert result is None
