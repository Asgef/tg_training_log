import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Import modules from our project
from src.configs.logging_config import setup_logging
from src.infrastructure.db.base import get_session
from src.infrastructure.db.repositories.user_repository import UserRepository
from src.infrastructure.db.repositories.workout_session_repository import (
    WorkoutSessionRepository,
)
from src.infrastructure.db.repositories.set_entry_repository import SetEntryRepository
from src.infrastructure.db.repositories.machine_repository import MachineRepository
from src.infrastructure.db.repositories.muscle_repository import MuscleRepository
from src.application.use_cases.registration import RegistrationUseCase
from src.application.use_cases.workout import WorkoutUseCase
from src.application.use_cases.machine_management import MachineManagementUseCase
from src.application.use_cases.google_sheets_export import GoogleSheetsExportUseCase
from src.infrastructure.services.google_sheets_client import GoogleSheetsClient
from src.infrastructure.web.handlers import registration, workout, machine, common
from src.infrastructure.web.middlewares import RegistrationCheckMiddleware

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global instances (simplified DI for now)
user_repo_instance: UserRepository = None  # type: ignore
registration_use_case_instance: RegistrationUseCase = None  # type: ignore
workout_session_repo_instance: WorkoutSessionRepository = None  # type: ignore
set_entry_repo_instance: SetEntryRepository = None  # type: ignore
workout_use_case_instance: WorkoutUseCase = None  # type: ignore
machine_repo_instance: MachineRepository = None  # type: ignore
muscle_repo_instance: MuscleRepository = None  # type: ignore
machine_management_use_case_instance: MachineManagementUseCase = None  # type: ignore
google_sheets_client_instance: GoogleSheetsClient = None  # type: ignore
google_sheets_export_use_case_instance: GoogleSheetsExportUseCase = None  # type: ignore


async def main() -> None:
    # Initialize Storage for FSM
    storage = MemoryStorage()

    # Initialize Bot and Dispatcher
    bot = Bot(os.getenv("BOT_TOKEN"), parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=storage)

    # --- Dependency Injection Setup (simplified) ---
    async for session in get_session():
        global user_repo_instance
        global registration_use_case_instance
        global workout_session_repo_instance
        global set_entry_repo_instance
        global workout_use_case_instance
        global machine_repo_instance
        global muscle_repo_instance
        global machine_management_use_case_instance
        global google_sheets_client_instance
        global google_sheets_export_use_case_instance

        user_repo_instance = UserRepository(session)
        workout_session_repo_instance = WorkoutSessionRepository(session)
        set_entry_repo_instance = SetEntryRepository(session)
        machine_repo_instance = MachineRepository(session)
        muscle_repo_instance = MuscleRepository(session)

        try:
            google_sheets_client_instance = (
                GoogleSheetsClient()
            )  # GoogleSheetsClient does not depend on session
        except RuntimeError as e:
            logger.error(
                f"Failed to initialize GoogleSheetsClient: {e}. Google Sheets functionality will be disabled."
            )
            google_sheets_client_instance = None  # Disable it if initialization fails

        registration_use_case_instance = RegistrationUseCase(user_repo_instance)
        workout_use_case_instance = WorkoutUseCase(
            workout_session_repo_instance, set_entry_repo_instance
        )
        machine_management_use_case_instance = MachineManagementUseCase(
            machine_repo_instance, muscle_repo_instance
        )
        google_sheets_export_use_case_instance = GoogleSheetsExportUseCase(
            user_repository=user_repo_instance,
            machine_repository=machine_repo_instance,
            set_entry_repository=set_entry_repo_instance,
            google_sheets_client=google_sheets_client_instance,
        )
        break

    # Inject into handlers and middlewares directly for now
    registration.user_repository = user_repo_instance
    registration.registration_use_case = registration_use_case_instance
    workout.workout_use_case = workout_use_case_instance
    machine.machine_management_use_case = machine_management_use_case_instance
    machine.muscle_repository = muscle_repo_instance
    common.google_sheets_export_use_case = google_sheets_export_use_case_instance
    RegistrationCheckMiddleware.user_repository = user_repo_instance

    # Register middlewares
    dp.message.middleware(RegistrationCheckMiddleware())
    dp.callback_query.middleware(RegistrationCheckMiddleware())

    # Register routers
    dp.include_router(registration.router)
    dp.include_router(workout.router)
    dp.include_router(machine.router)
    dp.include_router(common.router)  # Register common router

    logger.info("Bot started polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Bot encountered an error: {e}")
