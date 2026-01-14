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
from src.container import Container
from src.infrastructure.web.handlers import registration, workout, machine, common
from src.infrastructure.web.middlewares import RegistrationCheckMiddleware  # Из middlewares.py файла
from src.infrastructure.web.middleware.database import DatabaseMiddleware  # Из middleware/ папки
from src.infrastructure.web.middleware.dependency_injection import DependencyInjectionMiddleware  # Из middleware/ папки

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная функция запуска бота."""
    
    # Инициализация контейнера зависимостей
    container = Container()
    container.config_provider.database_url.from_value(config.database_url)
    container.config_provider.database_echo.from_value(False)  # Отключить echo в production
    
    # Инициализация хранилища для FSM
    storage = MemoryStorage()
    
    # Инициализация бота и диспетчера
    bot = Bot(
        config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware (порядок ОЧЕНЬ важен!)
    # 1. Database (создаёт сессию для каждого запроса)
    dp.message.middleware(DatabaseMiddleware(container.session_factory()))
    dp.callback_query.middleware(DatabaseMiddleware(container.session_factory()))
    
    # 2. Dependency Injection (использует сессию из DatabaseMiddleware)
    dp.message.middleware(DependencyInjectionMiddleware(container))
    dp.callback_query.middleware(DependencyInjectionMiddleware(container))
    
    # 3. Registration Check (использует зависимости из DependencyInjectionMiddleware)
    dp.message.middleware(RegistrationCheckMiddleware())
    dp.callback_query.middleware(RegistrationCheckMiddleware())
    
    # Регистрация роутеров
    dp.include_router(registration.router)
    dp.include_router(workout.router)
    dp.include_router(machine.router)
    dp.include_router(common.router)
    
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
    
    try:
        await dp.start_polling(bot)
    finally:
        # Graceful shutdown
        logger.info("Shutting down...")
        await bot.session.close()
        # Закрыть все сессии БД
        await container.engine().dispose()
        logger.info("Bot stopped successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"Бот столкнулся с ошибкой: {e}")
