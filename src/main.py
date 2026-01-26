import asyncio
import os
import signal
import sys
import traceback
from typing import Optional, Any

import structlog
import rollbar
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat
from alembic import command
from alembic.config import Config as AlembicConfig

# Импорт модулей проекта
from src.configs.config import config
from src.configs.logging_config import setup_logging
from src.container import Container
from src.infrastructure.web.handlers import registration, workout, machine, common
from src.infrastructure.web.middlewares import RegistrationCheckMiddleware  # Из middlewares.py файла
from src.infrastructure.web.middleware.logging import LoggingMiddleware  # Из middleware/ папки
from src.infrastructure.web.middleware.database import DatabaseMiddleware  # Из middleware/ папки
from src.infrastructure.web.middleware.dependency_injection import DependencyInjectionMiddleware  # Из middleware/ папки
from src.infrastructure.web.middleware.idempotency import IdempotencyMiddleware  # Из middleware/ папки
from src.infrastructure.web.middleware.error_handling import ErrorHandlingMiddleware  # Из middleware/ папки

# Настройка логирования из конфига
setup_logging(
    log_level=config.log_level,
    log_file_path=config.log_file_path,
    log_rotate_when=config.log_rotate_when,
    log_rotate_interval=config.log_rotate_interval,
    log_rotate_backup_count=config.log_rotate_backup_count,
)
logger = structlog.get_logger(__name__)

# Инициализация Rollbar для мониторинга ошибок
if config.rollbar_token:
    rollbar.init(
        access_token=config.rollbar_token,
        environment=config.rollbar_environment,
        handler='async',  # Использует httpx для async отправки
        code_version=config.rollbar_code_version if config.rollbar_code_version else None,
        allow_logging_basic_config=False,  # Не конфликтует с structlog
        timeout=15,  # Увеличенный таймаут для HTTP запросов (по умолчанию 3 сек - слишком мало)
        log_all_rate_limited_items=True,  # Логировать предупреждения о rate limit
    )
    logger.info(
        "Rollbar инициализирован",
        environment=config.rollbar_environment,
        code_version=config.rollbar_code_version if config.rollbar_code_version else "не указана",
        timeout=15,
    )
else:
    logger.warning("Rollbar токен не установлен, мониторинг ошибок отключен")

# Глобальные переменные для graceful shutdown
_shutdown_event: Optional[asyncio.Event] = None
_bot_instance: Optional[Bot] = None
_dispatcher_instance: Optional[Dispatcher] = None
_container_instance: Optional[Container] = None
_storage_instance: Optional[MemoryStorage] = None


def _run_migrations_sync(database_url: str) -> None:
    """Запускает Alembic upgrade до head."""
    try:
        logger.debug(f"Инициализация Alembic конфигурации...")
        alembic_ini = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        if not os.path.exists(alembic_ini):
            raise FileNotFoundError(f"Alembic конфигурационный файл не найден: {alembic_ini}")
        
        logger.debug(f"Загрузка конфигурации из {alembic_ini}")
        alembic_cfg = AlembicConfig(alembic_ini)
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        logger.debug(f"Запуск команды upgrade до head...")
        command.upgrade(alembic_cfg, "head")
        logger.debug("Alembic upgrade выполнен успешно")
    except Exception as e:
        logger.error(
            "Ошибка при выполнении миграций Alembic",
            error_type=type(e).__name__,
            error_message=str(e),
            alembic_ini=alembic_ini if 'alembic_ini' in locals() else None,
            database_url=database_url[:50] + "..." if len(database_url) > 50 else database_url,
            exc_info=True
        )
        raise


async def run_migrations(database_url: str) -> None:
    """Запускает миграции в отдельном потоке, чтобы не блокировать loop."""
    logger.info("Запуск Alembic миграций...", database_url=database_url[:50] + "..." if len(database_url) > 50 else database_url)
    try:
        await asyncio.to_thread(_run_migrations_sync, database_url)
        logger.info("Alembic миграции завершены успешно")
    except Exception as e:
        logger.exception(
            "Критическая ошибка при выполнении миграций",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True
        )
        raise


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
    
    def signal_handler(signum: int, frame: Any) -> None:
        """Обработчик сигналов SIGTERM и SIGINT."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Получен сигнал {signal_name}, инициирую graceful shutdown...")
        if _shutdown_event:
            _shutdown_event.set()
    
    # Регистрируем обработчики для SIGTERM и SIGINT
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logger.debug("Обработчики сигналов зарегистрированы (SIGTERM, SIGINT)")


def _rollbar_task_exception_handler(loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
    """Обработчик исключений для фоновых задач Rollbar.
    
    Rollbar запускает фоновые задачи для отправки ошибок, и если они падают
    с исключениями (например, ConnectTimeout), они не обрабатываются.
    Этот обработчик перехватывает такие исключения и логирует их.
    """
    exception = context.get('exception')
    task = context.get('task')
    message = context.get('message', 'Unhandled exception in task')
    
    # Игнорируем CancelledError - это нормальное завершение задач
    if isinstance(exception, asyncio.CancelledError):
        return
    
    # Логируем исключения из Rollbar задач
    if task and 'rollbar' in str(task).lower():
        logger.warning(
            "Исключение в фоновой задаче Rollbar",
            event_type="rollbar_background_task_error",
            message=message,
            exception_type=type(exception).__name__ if exception else None,
            exception_message=str(exception) if exception else None,
            task_name=str(task),
        )
    else:
        # Для других задач логируем как ошибку
        logger.error(
            "Необработанное исключение в фоновой задаче",
            event_type="unhandled_background_task_error",
            message=message,
            exception_type=type(exception).__name__ if exception else None,
            exception_message=str(exception) if exception else None,
            task_name=str(task),
            exc_info=exception,
        )


async def main() -> None:
    """Главная функция запуска бота."""
    global _shutdown_event, _bot_instance, _dispatcher_instance, _container_instance, _storage_instance
    
    # Инициализация события для shutdown
    _shutdown_event = asyncio.Event()
    
    # Настройка обработчика исключений для фоновых задач (включая Rollbar)
    # Обрабатывает исключения в фоновых задачах, которые не были await'нуты
    # (например, задачи Rollbar для отправки ошибок)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Если loop ещё не запущен, используем get_event_loop()
        loop = asyncio.get_event_loop()
    loop.set_exception_handler(_rollbar_task_exception_handler)
    
    # Настройка обработчиков сигналов
    setup_signal_handlers()

    # Прогон миграций до запуска бота
    try:
        await run_migrations(config.database_url)
    except Exception as e:
        logger.exception(f"Ошибка при запуске миграций: {e}")
        raise
    
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
    
    # Настройка команд бота (общие команды для всех пользователей)
    bot_commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="menu", description="Показать меню"),
        BotCommand(command="workout_start", description="Начать тренировку"),
        BotCommand(command="workout_end", description="Завершить тренировку"),
        BotCommand(command="record_set", description="Записать подход"),
        BotCommand(command="machines", description="Управление тренажерами"),
        BotCommand(command="google_sheets", description="Настройка Google Sheets"),
    ]
    
    # Устанавливаем общие команды для всех пользователей
    await bot.set_my_commands(bot_commands)
    
    # Устанавливаем команды для администраторов (включая тестовую команду Rollbar)
    if config.rollbar_token and config.admin_ids:
        admin_commands = bot_commands + [
            BotCommand(command="test_rollbar", description="Тест Rollbar (только админы)")
        ]
        
        # Устанавливаем команды для каждого администратора отдельно
        for admin_id in config.admin_ids:
            try:
                await bot.set_my_commands(
                    admin_commands,
                    scope=BotCommandScopeChat(chat_id=admin_id)
                )
                logger.debug(
                    "Команды для администратора установлены",
                    admin_id=admin_id,
                )
            except Exception as e:
                logger.warning(
                    "Не удалось установить команды для администратора",
                    admin_id=admin_id,
                    error=str(e),
                )
    
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
        # Явное логирование с полным traceback
        logger.exception(
            "Критическая ошибка при запуске бота",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        # Отправка критичной ошибки в Rollbar
        if config.rollbar_token:
            try:
                rollbar.report_exc_info(exc_info=sys.exc_info(), level='critical')
            except Exception as rollbar_error:
                # Если Rollbar сам упал, логируем, но не прерываем выполнение
                logger.error(
                    "Не удалось отправить ошибку в Rollbar",
                    rollbar_error=str(rollbar_error),
                    exc_info=True,
                )
        # Также выводим в stderr на случай, если логирование сломано
        print("КРИТИЧЕСКАЯ ОШИБКА (вывод в stderr):", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
