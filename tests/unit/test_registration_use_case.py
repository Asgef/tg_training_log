"""Unit тесты для RegistrationUseCase."""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from src.application.use_cases.registration import RegistrationUseCase
from src.domain.models import User


@pytest.mark.unit
class TestRegistrationUseCase:
    """Тесты для RegistrationUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Создаёт мок UserRepository."""
        return AsyncMock()

    @pytest.fixture
    def registration_use_case(self, mock_user_repository):
        """Создаёт экземпляр RegistrationUseCase с моком репозитория."""
        return RegistrationUseCase(user_repository=mock_user_repository)

    @pytest.fixture
    def test_user(self):
        """Создаёт тестового пользователя."""
        return User(
            id=123456789,
            telegram_username="testuser",
            telegram_firstname="Test",
            telegram_lastname="User",
            is_registered=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            timezone="Europe/Berlin",
        )

    async def test_request_registration_success(
        self, registration_use_case, mock_user_repository, test_user
    ):
        """Тест успешного запроса регистрации."""
        # Настраиваем мок: пользователь не существует
        mock_user_repository.get_by_telegram_id.return_value = None
        mock_user_repository.add.return_value = test_user

        # Вызываем метод
        result = await registration_use_case.request_registration(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            description="Test description",
        )

        # Проверяем результат
        assert result is True
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)
        mock_user_repository.add.assert_called_once()
        added_user = mock_user_repository.add.call_args[0][0]
        assert added_user.id == 123456789
        assert added_user.telegram_username == "testuser"
        assert added_user.is_registered is False

    async def test_request_registration_user_already_exists(
        self, registration_use_case, mock_user_repository, test_user
    ):
        """Тест запроса регистрации для существующего пользователя."""
        # Настраиваем мок: пользователь уже существует
        mock_user_repository.get_by_telegram_id.return_value = test_user

        # Вызываем метод
        result = await registration_use_case.request_registration(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            description="Test description",
        )

        # Проверяем результат
        assert result is False
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)
        mock_user_repository.add.assert_not_called()

    async def test_request_registration_repository_error(
        self, registration_use_case, mock_user_repository
    ):
        """Тест обработки ошибки репозитория при запросе регистрации."""
        # Настраиваем мок: выбрасываем исключение
        mock_user_repository.get_by_telegram_id.side_effect = Exception("DB Error")

        # Вызываем метод
        result = await registration_use_case.request_registration(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            description="Test description",
        )

        # Проверяем, что ошибка обработана и возвращён False
        assert result is False

    async def test_approve_registration_success(
        self, registration_use_case, mock_user_repository, test_user
    ):
        """Тест успешного одобрения регистрации."""
        # Настраиваем мок
        mock_user_repository.get_by_id.return_value = test_user
        mock_user_repository.update.return_value = test_user

        # Вызываем метод
        result = await registration_use_case.approve_registration(user_id=123456789)

        # Проверяем результат
        assert result is True
        mock_user_repository.get_by_id.assert_called_once_with(123456789)
        mock_user_repository.update.assert_called_once()
        updated_user = mock_user_repository.update.call_args[0][0]
        assert updated_user.is_registered is True

    async def test_approve_registration_user_not_found(
        self, registration_use_case, mock_user_repository
    ):
        """Тест одобрения регистрации для несуществующего пользователя."""
        # Настраиваем мок: пользователь не найден
        mock_user_repository.get_by_id.return_value = None

        # Вызываем метод
        result = await registration_use_case.approve_registration(user_id=123456789)

        # Проверяем результат
        assert result is False
        mock_user_repository.get_by_id.assert_called_once_with(123456789)
        mock_user_repository.update.assert_not_called()

    async def test_approve_registration_already_registered(
        self, registration_use_case, mock_user_repository, test_user
    ):
        """Тест одобрения регистрации для уже зарегистрированного пользователя."""
        # Настраиваем мок: пользователь уже зарегистрирован
        test_user.is_registered = True
        mock_user_repository.get_by_id.return_value = test_user

        # Вызываем метод
        result = await registration_use_case.approve_registration(user_id=123456789)

        # Проверяем результат
        assert result is False
        mock_user_repository.get_by_id.assert_called_once_with(123456789)
        mock_user_repository.update.assert_not_called()

    async def test_reject_registration_success(
        self, registration_use_case, mock_user_repository, test_user
    ):
        """Тест успешного отклонения регистрации."""
        # Настраиваем мок
        mock_user_repository.get_by_id.return_value = test_user
        mock_user_repository.delete.return_value = None

        # Вызываем метод
        result = await registration_use_case.reject_registration(user_id=123456789)

        # Проверяем результат
        assert result is True
        mock_user_repository.get_by_id.assert_called_once_with(123456789)
        mock_user_repository.delete.assert_called_once_with(123456789)

    async def test_reject_registration_user_not_found(
        self, registration_use_case, mock_user_repository
    ):
        """Тест отклонения регистрации для несуществующего пользователя."""
        # Настраиваем мок: пользователь не найден
        mock_user_repository.get_by_id.return_value = None

        # Вызываем метод
        result = await registration_use_case.reject_registration(user_id=123456789)

        # Проверяем результат
        assert result is False
        mock_user_repository.get_by_id.assert_called_once_with(123456789)
        mock_user_repository.delete.assert_not_called()

    async def test_get_user_by_telegram_id_success(
        self, registration_use_case, mock_user_repository, test_user
    ):
        """Тест успешного получения пользователя по Telegram ID."""
        # Настраиваем мок
        mock_user_repository.get_by_telegram_id.return_value = test_user

        # Вызываем метод
        result = await registration_use_case.get_user_by_telegram_id(telegram_id=123456789)

        # Проверяем результат
        assert result is not None
        assert result.id == 123456789
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)

    async def test_get_user_by_telegram_id_not_found(
        self, registration_use_case, mock_user_repository
    ):
        """Тест получения несуществующего пользователя."""
        # Настраиваем мок: пользователь не найден
        mock_user_repository.get_by_telegram_id.return_value = None

        # Вызываем метод
        result = await registration_use_case.get_user_by_telegram_id(telegram_id=123456789)

        # Проверяем результат
        assert result is None
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)

    async def test_check_user_registered_true(
        self, registration_use_case, mock_user_repository, test_user
    ):
        """Тест проверки регистрации для зарегистрированного пользователя."""
        # Настраиваем мок: пользователь зарегистрирован
        test_user.is_registered = True
        mock_user_repository.get_by_telegram_id.return_value = test_user

        # Вызываем метод
        result = await registration_use_case.check_user_registered(telegram_id=123456789)

        # Проверяем результат
        assert result is True
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)

    async def test_check_user_registered_false(
        self, registration_use_case, mock_user_repository, test_user
    ):
        """Тест проверки регистрации для незарегистрированного пользователя."""
        # Настраиваем мок: пользователь не зарегистрирован
        test_user.is_registered = False
        mock_user_repository.get_by_telegram_id.return_value = test_user

        # Вызываем метод
        result = await registration_use_case.check_user_registered(telegram_id=123456789)

        # Проверяем результат
        assert result is False
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)

    async def test_check_user_registered_not_found(
        self, registration_use_case, mock_user_repository
    ):
        """Тест проверки регистрации для несуществующего пользователя."""
        # Настраиваем мок: пользователь не найден
        mock_user_repository.get_by_telegram_id.return_value = None

        # Вызываем метод
        result = await registration_use_case.check_user_registered(telegram_id=123456789)

        # Проверяем результат
        assert result is False
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)
