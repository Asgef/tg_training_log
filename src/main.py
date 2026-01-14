import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

# Импорт модулей проекта
from src.configs.logging_config import setup_logging
from src.configs.config import config
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

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

# Глобальные экземпляры (упрощённая DI пока)
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
    # Инициализация хранилища для FSM
    storage = MemoryStorage()

    # Инициализация бота и диспетчера
    bot = Bot(
        config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)

    # --- Настройка Dependency Injection (упрощённая) ---
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
            )  # GoogleSheetsClient не зависит от сессии
        except RuntimeError as e:
            logger.error(
                f"Не удалось инициализировать GoogleSheetsClient: {e}. Функциональность Google Sheets будет отключена."
            )
            google_sheets_client_instance = None  # Отключить, если инициализация не удалась

        registration_use_case_instance = RegistrationUseCase(user_repo_instance)
        workout_use_case_instance = WorkoutUseCase(
            workout_session_repo_instance, set_entry_repo_instance, machine_repo_instance
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

    # Прямая инъекция в хэндлеры и middleware пока
    registration.user_repository = user_repo_instance
    registration.registration_use_case = registration_use_case_instance
    workout.workout_use_case = workout_use_case_instance
    machine.machine_management_use_case = machine_management_use_case_instance
    machine.muscle_repository = muscle_repo_instance
    common.google_sheets_export_use_case = google_sheets_export_use_case_instance
    RegistrationCheckMiddleware.user_repository = user_repo_instance

    # Регистрация middleware
    dp.message.middleware(RegistrationCheckMiddleware())
    dp.callback_query.middleware(RegistrationCheckMiddleware())

    # Регистрация роутеров
    dp.include_router(registration.router)
    dp.include_router(workout.router)
    dp.include_router(machine.router)
    dp.include_router(common.router)  # Регистрация общего роутера

    # Настройка команд бота
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="menu", description="Показать меню"),
        BotCommand(command="workout_start", description="Начать тренировку"),
        BotCommand(command="workout_end", description="Завершить тренировку"),
        BotCommand(command="record_set", description="Записать подход"),
        BotCommand(command="machines", description="Управление тренажерами"),
        BotCommand(command="google_sheets", description="Настройка Google Sheets"),
    ])

    logger.info("Бот начал polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"Бот столкнулся с ошибкой: {e}")
