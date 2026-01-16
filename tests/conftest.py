"""Pytest конфигурация и общие fixtures для всех тестов."""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy import event

from src.domain.models import Base
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
from faker import Faker


# Настройка Faker для генерации тестовых данных
fake = Faker("ru_RU")


@pytest.fixture(scope="session")
def event_loop():
    """Создаёт event loop для всей сессии тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Создаёт тестовый engine с SQLite in-memory БД.
    
    Используется для быстрых unit тестов.
    Каждый тест получает чистую БД.
    Включает проверку foreign key constraints для SQLite.
    """
    # SQLite in-memory для быстрых тестов
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,  # Для in-memory БД
        connect_args={"check_same_thread": False},
    )
    
    # Включаем проверку foreign keys для SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Включает проверку foreign key constraints в SQLite."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Создаём все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Очищаем после теста
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Создаёт тестовую сессию БД.
    
    Автоматически делает rollback после каждого теста,
    чтобы изолировать тесты друг от друга.
    """
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()  # Откатываем изменения после теста


@pytest.fixture
async def user_repository(test_session: AsyncSession) -> UserRepository:
    """Fixture для UserRepository."""
    return UserRepository(session=test_session)


@pytest.fixture
async def machine_repository(test_session: AsyncSession) -> MachineRepository:
    """Fixture для MachineRepository."""
    return MachineRepository(session=test_session)


@pytest.fixture
async def muscle_repository(test_session: AsyncSession) -> MuscleRepository:
    """Fixture для MuscleRepository."""
    return MuscleRepository(session=test_session)


@pytest.fixture
async def workout_session_repository(test_session: AsyncSession) -> WorkoutSessionRepository:
    """Fixture для WorkoutSessionRepository."""
    return WorkoutSessionRepository(session=test_session)


@pytest.fixture
async def set_entry_repository(test_session: AsyncSession) -> SetEntryRepository:
    """Fixture для SetEntryRepository."""
    return SetEntryRepository(session=test_session)


@pytest.fixture
async def processed_update_repository(test_session: AsyncSession) -> ProcessedUpdateRepository:
    """Fixture для ProcessedUpdateRepository."""
    return ProcessedUpdateRepository(session=test_session)


@pytest.fixture
async def registration_use_case(
    user_repository: UserRepository,
) -> RegistrationUseCase:
    """Fixture для RegistrationUseCase."""
    return RegistrationUseCase(user_repository=user_repository)


@pytest.fixture
async def workout_use_case(
    workout_session_repository: WorkoutSessionRepository,
    set_entry_repository: SetEntryRepository,
    machine_repository: MachineRepository,
) -> WorkoutUseCase:
    """Fixture для WorkoutUseCase."""
    return WorkoutUseCase(
        workout_session_repository=workout_session_repository,
        set_entry_repository=set_entry_repository,
        machine_repository=machine_repository,
    )


@pytest.fixture
async def machine_management_use_case(
    machine_repository: MachineRepository,
    muscle_repository: MuscleRepository,
) -> MachineManagementUseCase:
    """Fixture для MachineManagementUseCase."""
    return MachineManagementUseCase(
        machine_repository=machine_repository,
        muscle_repository=muscle_repository,
    )


@pytest.fixture
async def google_sheets_export_use_case(
    user_repository: UserRepository,
    machine_repository: MachineRepository,
    set_entry_repository: SetEntryRepository,
) -> GoogleSheetsExportUseCase:
    """Fixture для GoogleSheetsExportUseCase.
    
    Внимание: требует мок для GoogleSheetsClient в реальных тестах.
    """
    # Для unit тестов можно использовать мок
    from unittest.mock import AsyncMock
    mock_google_sheets_client = AsyncMock()
    
    return GoogleSheetsExportUseCase(
        user_repository=user_repository,
        machine_repository=machine_repository,
        set_entry_repository=set_entry_repository,
        google_sheets_client=mock_google_sheets_client,
    )


# Fixtures для тестовых данных
@pytest.fixture
def test_user_id() -> int:
    """Возвращает тестовый user_id."""
    return 123456789


@pytest.fixture
def test_user_data(test_user_id: int) -> dict:
    """Возвращает данные для создания тестового пользователя."""
    return {
        "id": test_user_id,
        "telegram_id": test_user_id,
        "telegram_username": fake.user_name(),
        "telegram_firstname": fake.first_name(),
        "telegram_lastname": fake.last_name(),
        "is_registered": False,
    }


@pytest.fixture
def test_machine_data() -> dict:
    """Возвращает данные для создания тестового тренажёра."""
    return {
        "name": fake.word().capitalize(),
        "user_id": 123456789,
    }
