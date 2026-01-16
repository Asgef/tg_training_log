"""Fixtures для E2E тестов."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator
import itertools
_update_counter = itertools.count(1)
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update, Message, User, Chat, CallbackQuery
from datetime import datetime, timezone
from aiogram.client.session.aiohttp import AiohttpSession

from src.container import Container
from src.infrastructure.web.handlers import registration, workout, common
from src.infrastructure.web.handlers.machine import router as machine_router
from src.infrastructure.web.middlewares import RegistrationCheckMiddleware
from src.infrastructure.web.middleware.logging import LoggingMiddleware
from src.infrastructure.web.middleware.database import DatabaseMiddleware
from src.infrastructure.web.middleware.dependency_injection import DependencyInjectionMiddleware
from src.infrastructure.web.middleware.idempotency import IdempotencyMiddleware
from src.infrastructure.web.middleware.error_handling import ErrorHandlingMiddleware


@pytest.fixture
async def bot() -> Bot:
    """Создаёт мок Bot для тестов."""
    # Используем реальный Bot, но с мок-сессией
    session = AsyncMock(spec=AiohttpSession)
    return Bot(token="123456:TEST_TOKEN", session=session)


@pytest.fixture
async def dispatcher(container: Container) -> Dispatcher:
    """Создаёт Dispatcher с подключенными handlers."""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    from src.configs.config import config
    config.admin_ids = [999999999]
    registration.ADMIN_IDS = config.admin_ids
    
    # Подключаем routers
    registration.router._parent_router = None
    workout.router._parent_router = None
    machine_router._parent_router = None
    common.router._parent_router = None
    dp.include_router(registration.router)
    dp.include_router(workout.router)
    dp.include_router(machine_router)
    dp.include_router(common.router)
    
    # Подключаем middlewares
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(DatabaseMiddleware(container.session_factory()))
    dp.callback_query.middleware(DatabaseMiddleware(container.session_factory()))
    dp.message.middleware(DependencyInjectionMiddleware(container))
    dp.callback_query.middleware(DependencyInjectionMiddleware(container))
    # Идемпотентность в e2e отключаем, чтобы не блокировать тестовые update_id
    dp.message.middleware(RegistrationCheckMiddleware())
    dp.message.middleware(ErrorHandlingMiddleware())
    dp.callback_query.middleware(ErrorHandlingMiddleware())
    
    return dp


@pytest.fixture
def container(test_session) -> Container:
    """Создаёт Container с тестовыми зависимостями."""
    # Создаём контейнер с тестовой сессией
    from src.infrastructure.db.repositories.user_repository import UserRepository
    from src.infrastructure.db.repositories.machine_repository import MachineRepository
    from src.infrastructure.db.repositories.muscle_repository import MuscleRepository
    from src.infrastructure.db.repositories.workout_session_repository import WorkoutSessionRepository
    from src.infrastructure.db.repositories.set_entry_repository import SetEntryRepository
    from src.infrastructure.db.repositories.processed_update_repository import ProcessedUpdateRepository
    from src.application.use_cases.registration import RegistrationUseCase
    from src.application.use_cases.workout import WorkoutUseCase
    from src.application.use_cases.machine_management import MachineManagementUseCase
    from src.application.use_cases.google_sheets_export import GoogleSheetsExportUseCase
    from unittest.mock import AsyncMock
    
    # Создаём репозитории с тестовой сессией
    user_repo = UserRepository(session=test_session)
    machine_repo = MachineRepository(session=test_session)
    muscle_repo = MuscleRepository(session=test_session)
    workout_repo = WorkoutSessionRepository(session=test_session)
    set_entry_repo = SetEntryRepository(session=test_session)
    processed_update_repo = ProcessedUpdateRepository(session=test_session)
    
    # Создаём use cases
    registration_uc = RegistrationUseCase(user_repository=user_repo)
    workout_uc = WorkoutUseCase(
        workout_session_repository=workout_repo,
        set_entry_repository=set_entry_repo,
        machine_repository=machine_repo,
    )
    machine_uc = MachineManagementUseCase(
        machine_repository=machine_repo,
        muscle_repository=muscle_repo,
    )
    google_sheets_uc = GoogleSheetsExportUseCase(
        user_repository=user_repo,
        machine_repository=machine_repo,
        set_entry_repository=set_entry_repo,
        google_sheets_client=AsyncMock(),  # Мок для Google Sheets
    )
    
    # Создаём мок контейнера
    mock_container = MagicMock(spec=Container)
    mock_container.user_repository.return_value = user_repo
    mock_container.machine_repository.return_value = machine_repo
    mock_container.muscle_repository.return_value = muscle_repo
    mock_container.workout_session_repository.return_value = workout_repo
    mock_container.set_entry_repository.return_value = set_entry_repo
    mock_container.processed_update_repository.return_value = processed_update_repo
    mock_container.registration_use_case.return_value = registration_uc
    mock_container.workout_use_case.return_value = workout_uc
    mock_container.machine_management_use_case.return_value = machine_uc
    mock_container.google_sheets_export_use_case.return_value = google_sheets_uc
    mock_container.session_factory.return_value = lambda: test_session
    
    return mock_container


def create_message_update(
    text: str,
    user_id: int = 123456789,
    username: str = "test_user",
    first_name: str = "Test",
    last_name: str = "User",
    chat_id: int = 123456789,
    update_id: int | None = None,
) -> Update:
    """Создаёт Update с Message для тестов."""
    user = User(
        id=user_id,
        is_bot=False,
        first_name=first_name,
        last_name=last_name,
        username=username,
    )
    chat = Chat(id=chat_id, type="private")
    message = Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=chat,
        from_user=user,
        text=text,
    )
    update_id = update_id if update_id is not None else next(_update_counter)
    return Update(update_id=update_id, message=message)


def create_callback_query_update(
    callback_data: str,
    user_id: int = 123456789,
    username: str = "test_user",
    first_name: str = "Test",
    last_name: str = "User",
    chat_id: int = 123456789,
    message_id: int = 1,
    update_id: int | None = None,
) -> Update:
    """Создаёт Update с CallbackQuery для тестов."""
    user = User(
        id=user_id,
        is_bot=False,
        first_name=first_name,
        last_name=last_name,
        username=username,
    )
    chat = Chat(id=chat_id, type="private")
    message = Message(
        message_id=message_id,
        date=datetime.now(timezone.utc),
        chat=chat,
        from_user=user,
        text="Test message",
    )
    callback_query = CallbackQuery(
        id="test_callback_id",
        from_user=user,
        chat_instance="test_chat_instance",
        data=callback_data,
        message=message,
    )
    update_id = update_id if update_id is not None else next(_update_counter)
    return Update(update_id=update_id, callback_query=callback_query)


@pytest.fixture
def test_user_id() -> int:
    """Возвращает тестовый user_id."""
    return 123456789


@pytest.fixture
def admin_user_id() -> int:
    """Возвращает тестовый admin_id."""
    return 999999999
