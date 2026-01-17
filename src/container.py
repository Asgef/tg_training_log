"""Контейнер зависимостей приложения.

Использует dependency-injector для управления зависимостями.
"""
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.configs.config import config
from src.infrastructure.db.repositories.user_repository import UserRepository
from src.infrastructure.db.repositories.machine_repository import MachineRepository
from src.infrastructure.db.repositories.machine_library_repository import (
    MachineLibraryRepository,
)
from src.infrastructure.db.repositories.muscle_repository import MuscleRepository
from src.infrastructure.db.repositories.workout_session_repository import WorkoutSessionRepository
from src.infrastructure.db.repositories.set_entry_repository import SetEntryRepository
from src.infrastructure.db.repositories.processed_update_repository import ProcessedUpdateRepository
from src.application.use_cases.registration import RegistrationUseCase
from src.application.use_cases.workout import WorkoutUseCase
from src.application.use_cases.machine_management import MachineManagementUseCase
from src.application.use_cases.machine_library import MachineLibraryUseCase
from src.application.use_cases.google_sheets_export import GoogleSheetsExportUseCase
from src.infrastructure.services.google_sheets_client import GoogleSheetsClient


class Container(containers.DeclarativeContainer):
    """Контейнер зависимостей приложения."""

    # Конфигурация
    config_provider = providers.Configuration()

    # Database engine
    engine = providers.Singleton(
        create_async_engine,
        config_provider.database_url,
        echo=config_provider.database_echo,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

    # Session factory
    session_factory = providers.Singleton(
        async_sessionmaker,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Repositories (Factory - создаются для каждого запроса)
    # Сессия будет передаваться через middleware
    user_repository = providers.Factory(
        UserRepository,
    )

    machine_repository = providers.Factory(
        MachineRepository,
    )

    machine_library_repository = providers.Factory(
        MachineLibraryRepository,
    )

    muscle_repository = providers.Factory(
        MuscleRepository,
    )

    workout_session_repository = providers.Factory(
        WorkoutSessionRepository,
    )

    set_entry_repository = providers.Factory(
        SetEntryRepository,
    )

    processed_update_repository = providers.Factory(
        ProcessedUpdateRepository,
    )

    # Services
    google_sheets_client = providers.Singleton(
        GoogleSheetsClient,
    )

    # Use Cases (Factory - создаются для каждого запроса)
    registration_use_case = providers.Factory(
        RegistrationUseCase,
    )

    workout_use_case = providers.Factory(
        WorkoutUseCase,
    )

    machine_management_use_case = providers.Factory(
        MachineManagementUseCase,
    )

    machine_library_use_case = providers.Factory(
        MachineLibraryUseCase,
    )

    google_sheets_export_use_case = providers.Factory(
        GoogleSheetsExportUseCase,
    )
