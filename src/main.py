import asyncio
import signal
from typing import Optional

import structlog
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
from src.infrastructure.web.middleware.logging import LoggingMiddleware  # Из middleware/ папки
from src.infrastructure.web.middleware.database import DatabaseMiddleware  # Из middleware/ папки
from src.infrastructure.web.middleware.dependency_injection import DependencyInjectionMiddleware  # Из middleware/ папки
from src.infrastructure.web.middleware.idempotency import IdempotencyMiddleware  # Из middleware/ папки
from src.infrastructure.web.middleware.error_handling import ErrorHandlingMiddleware  # Из middleware/ папки

# Настройка логирования
setup_logging()
logger = structlog.get_logger(__name__)

# Глобальные переменные для graceful shutdown
_shutdown_event: Optional[asyncio.Event] = None
_bot_instance: Optional[Bot] = None
_dispatcher_instance: Optional[Dispatcher] = None
_container_instance: Optional[Container] = None
_storage_instance: Optional[MemoryStorage] = None


async def graceful_shutdown() -> None:
    """Корректное завершение работы бота."""
    global _bot_instance, _dispatcher_instance, _container_instance, _storage_instance
    
    logger.info("Начало graceful shutdown...")
    
    # 1. Остановить polling
    if _dispatcher_instance:
        try:
            logger.info("Остановка polling...")
            await _dispatcher_instance.stop_polling()
            logger.info("Polling остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке polling: {e}", exc_info=True)
    
    # 2. Закрыть сессию бота
    if _bot_instance:
        try:
            logger.info("Закрытие сессии бота...")
            await _bot_instance.session.close()
            logger.info("Сессия бота закрыта")
        except Exception as e:
            logger.error(f"Ошибка при закрытии сессии бота: {e}", exc_info=True)
    
    # 3. Закрыть FSM storage (для MemoryStorage это не критично, но для Redis важно)
    if _storage_instance:
        try:
            logger.info("Закрытие FSM storage...")
            # Проверяем наличие метода close() (может отсутствовать у MemoryStorage)
            if hasattr(_storage_instance, 'close'):
                close_method = getattr(_storage_instance, 'close')
                if asyncio.iscoroutinefunction(close_method):
                    await close_method()
                else:
                    close_method()
            logger.info("FSM storage закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии FSM storage: {e}", exc_info=True)
    
    # 4. Закрыть соединения с БД
    if _container_instance:
        try:
            logger.info("Закрытие соединений с БД...")
            engine = _container_instance.engine()
            await engine.dispose()
            logger.info("Соединения с БД закрыты")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединений с БД: {e}", exc_info=True)
    
    # 5. Отменить все активные задачи (кроме текущей)
    try:
        logger.info("Отмена активных задач...")
        tasks = [task for task in asyncio.all_tasks() if task != asyncio.current_task()]
        if tasks:
            logger.info(f"Найдено {len(tasks)} активных задач, отмена...")
            for task in tasks:
                task.cancel()
            # Ждём завершения отменённых задач
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Активные задачи отменены")
    except Exception as e:
        logger.error(f"Ошибка при отмене активных задач: {e}", exc_info=True)
    
    logger.info("Graceful shutdown завершён успешно")


def setup_signal_handlers() -> None:
    """Настройка обработчиков сигналов для graceful shutdown."""
    global _shutdown_event
    
    def signal_handler(signum: int, frame) -> None:
        """Обработчик сигналов SIGTERM и SIGINT."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Получен сигнал {signal_name}, инициирую graceful shutdown...")
        if _shutdown_event:
            _shutdown_event.set()
    
    # Регистрируем обработчики для SIGTERM и SIGINT
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logger.info("Обработчики сигналов зарегистрированы (SIGTERM, SIGINT)")


async def main() -> None:
    """Главная функция запуска бота."""
    global _shutdown_event, _bot_instance, _dispatcher_instance, _container_instance, _storage_instance
    
    # Инициализация события для shutdown
    _shutdown_event = asyncio.Event()
    
    # Настройка обработчиков сигналов
    setup_signal_handlers()
    
    # Инициализация контейнера зависимостей
    container = Container()
    _container_instance = container
    container.config_provider.database_url.from_value(config.database_url)
    container.config_provider.database_echo.from_value(False)  # Отключить echo в production
    
    # Инициализация хранилища для FSM
    storage = MemoryStorage()
    _storage_instance = storage
    
    # Инициализация бота и диспетчера
    bot = Bot(
        config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    _bot_instance = bot
    dp = Dispatcher(storage=storage)
    _dispatcher_instance = dp
    
    # Регистрация middleware (порядок ОЧЕНЬ важен!)
    # 0. Logging (добавляет correlation_id и контекст - должен быть ПЕРВЫМ)
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    
    # 1. Database (создаёт сессию для каждого запроса)
    dp.message.middleware(DatabaseMiddleware(container.session_factory()))
    dp.callback_query.middleware(DatabaseMiddleware(container.session_factory()))
    
    # 2. Dependency Injection (использует сессию из DatabaseMiddleware)
    dp.message.middleware(DependencyInjectionMiddleware(container))
    dp.callback_query.middleware(DependencyInjectionMiddleware(container))
    
    # 3. Idempotency (использует репозиторий из DependencyInjectionMiddleware)
    dp.message.middleware(IdempotencyMiddleware())
    dp.callback_query.middleware(IdempotencyMiddleware())
    
    # 4. Registration Check (использует зависимости из DependencyInjectionMiddleware)
    dp.message.middleware(RegistrationCheckMiddleware())
    dp.callback_query.middleware(RegistrationCheckMiddleware())
    
    # 5. Error Handling (должен быть ПОСЛЕДНИМ, чтобы перехватывать все ошибки)
    dp.message.middleware(ErrorHandlingMiddleware())
    dp.callback_query.middleware(ErrorHandlingMiddleware())
    
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
        # Запускаем polling в фоновой задаче
        polling_task = asyncio.create_task(dp.start_polling(bot))
        
        # Запускаем задачу для ожидания сигнала shutdown
        shutdown_wait_task = asyncio.create_task(_shutdown_event.wait())
        
        # Ждём либо завершения polling, либо сигнала shutdown
        done, pending = await asyncio.wait(
            [polling_task, shutdown_wait_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Если получен сигнал shutdown, останавливаем polling
        if _shutdown_event.is_set():
            logger.info("Получен сигнал shutdown, останавливаю polling...")
            # Останавливаем polling через метод dispatcher
            try:
                await dp.stop_polling()
            except Exception as e:
                logger.error(f"Ошибка при остановке polling: {e}", exc_info=True)
            # Отменяем задачу polling, если она ещё выполняется
            if not polling_task.done():
                polling_task.cancel()
                try:
                    await polling_task
                except asyncio.CancelledError:
                    logger.info("Polling задача отменена")
        
        # Отменяем задачу ожидания shutdown, если она ещё выполняется
        if not shutdown_wait_task.done():
            shutdown_wait_task.cancel()
            try:
                await shutdown_wait_task
            except asyncio.CancelledError:
                pass
        
    except Exception as e:
        logger.exception(f"Ошибка во время работы бота: {e}")
    finally:
        # Graceful shutdown с таймаутом 30 секунд
        try:
            await asyncio.wait_for(graceful_shutdown(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("Graceful shutdown превысил таймаут 30 секунд, принудительное завершение")
        except Exception as e:
            logger.exception(f"Ошибка во время graceful shutdown: {e}")
        finally:
            logger.info("Bot stopped successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (KeyboardInterrupt)")
    except Exception as e:
        logger.exception(f"Бот столкнулся с ошибкой: {e}")
