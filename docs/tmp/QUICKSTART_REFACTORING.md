# Быстрый старт: Рефакторинг проекта

**Цель:** Пошаговая инструкция для начала рефакторинга с нуля.

---

## 🚀 Начало работы (День 1)

### Шаг 1: Создать ветку для рефакторинга

```bash
git checkout -b refactor/critical-fixes-sprint-1
```

### Шаг 2: Установить необходимые инструменты

```bash
# Добавить в pyproject.toml
uv add --dev dependency-injector
uv add --dev mypy
uv add --dev pytest pytest-asyncio pytest-cov
uv add --dev pre-commit
```

### Шаг 3: Настроить pre-commit (опционально)

```bash
# Создать .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
EOF

# Установить хуки
pre-commit install
```

---

## 📝 TASK-001: Внедрить DI контейнер (День 1-3)

### Шаг 1: Создать файл контейнера

```bash
touch src/container.py
```

### Шаг 2: Определить контейнер

```python
# src/container.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.configs.config import config
from src.infrastructure.db.repositories.user_repository import UserRepository
from src.infrastructure.db.repositories.machine_repository import MachineRepository
from src.infrastructure.db.repositories.muscle_repository import MuscleRepository
from src.infrastructure.db.repositories.workout_session_repository import WorkoutSessionRepository
from src.infrastructure.db.repositories.set_entry_repository import SetEntryRepository
from src.application.use_cases.registration import RegistrationUseCase
from src.application.use_cases.workout import WorkoutUseCase
from src.application.use_cases.machine_management import MachineManagementUseCase
from src.application.use_cases.google_sheets_export import GoogleSheetsExportUseCase
from src.infrastructure.services.google_sheets_client import GoogleSheetsClient


class Container(containers.DeclarativeContainer):
    """Контейнер зависимостей приложения."""

    # Конфигурация
    config = providers.Configuration()

    # Database engine
    engine = providers.Singleton(
        create_async_engine,
        config.database_url,
        echo=config.database_echo,
        pool_pre_ping=True,
    )

    # Session factory
    session_factory = providers.Singleton(
        sessionmaker,
        engine.provided,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Repositories (Factory - новая сессия для каждого запроса)
    user_repository = providers.Factory(
        UserRepository,
        session=providers.Callable(lambda factory: factory(), factory=session_factory.provided),
    )

    machine_repository = providers.Factory(
        MachineRepository,
        session=providers.Callable(lambda factory: factory(), factory=session_factory.provided),
    )

    muscle_repository = providers.Factory(
        MuscleRepository,
        session=providers.Callable(lambda factory: factory(), factory=session_factory.provided),
    )

    workout_session_repository = providers.Factory(
        WorkoutSessionRepository,
        session=providers.Callable(lambda factory: factory(), factory=session_factory.provided),
    )

    set_entry_repository = providers.Factory(
        SetEntryRepository,
        session=providers.Callable(lambda factory: factory(), factory=session_factory.provided),
    )

    # Services
    google_sheets_client = providers.Singleton(GoogleSheetsClient)

    # Use Cases
    registration_use_case = providers.Factory(
        RegistrationUseCase,
        user_repository=user_repository,
    )

    workout_use_case = providers.Factory(
        WorkoutUseCase,
        workout_session_repository=workout_session_repository,
        set_entry_repository=set_entry_repository,
        machine_repository=machine_repository,
    )

    machine_management_use_case = providers.Factory(
        MachineManagementUseCase,
        machine_repository=machine_repository,
        muscle_repository=muscle_repository,
    )

    google_sheets_export_use_case = providers.Factory(
        GoogleSheetsExportUseCase,
        user_repository=user_repository,
        machine_repository=machine_repository,
        set_entry_repository=set_entry_repository,
        google_sheets_client=google_sheets_client,
    )
```

### Шаг 3: Создать middleware для dependency injection

```bash
touch src/infrastructure/web/middlewares/dependency_injection.py
```

```python
# src/infrastructure/web/middlewares/dependency_injection.py
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.container import Container


class DependencyInjectionMiddleware(BaseMiddleware):
    """Middleware для инъекции зависимостей в handlers."""

    def __init__(self, container: Container):
        self.container = container
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Инъецируем use cases в data
        data["registration_use_case"] = self.container.registration_use_case()
        data["workout_use_case"] = self.container.workout_use_case()
        data["machine_management_use_case"] = self.container.machine_management_use_case()
        data["google_sheets_export_use_case"] = self.container.google_sheets_export_use_case()
        data["muscle_repository"] = self.container.muscle_repository()
        data["user_repository"] = self.container.user_repository()

        return await handler(event, data)
```

### Шаг 4: Обновить main.py

```python
# src/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from src.configs.logging_config import setup_logging
from src.configs.config import config
from src.container import Container
from src.infrastructure.web.handlers import registration, workout, machine, common
from src.infrastructure.web.middlewares.registration_check import RegistrationCheckMiddleware
from src.infrastructure.web.middlewares.dependency_injection import DependencyInjectionMiddleware

setup_logging()
logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная функция запуска бота."""
    
    # Инициализация контейнера зависимостей
    container = Container()
    container.config.database_url.from_value(config.database_url)
    container.config.database_echo.from_value(False)  # Отключить echo в production
    
    # Инициализация хранилища для FSM
    storage = MemoryStorage()
    
    # Инициализация бота и диспетчера
    bot = Bot(
        config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware (порядок важен!)
    # 1. Dependency Injection (должен быть первым)
    dp.message.middleware(DependencyInjectionMiddleware(container))
    dp.callback_query.middleware(DependencyInjectionMiddleware(container))
    
    # 2. Registration Check
    registration_check_middleware = RegistrationCheckMiddleware()
    dp.message.middleware(registration_check_middleware)
    dp.callback_query.middleware(registration_check_middleware)
    
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


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"Бот столкнулся с ошибкой: {e}")
```

### Шаг 5: Обновить middlewares.py

```python
# src/infrastructure/web/middlewares.py
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from src.configs.config import config


class RegistrationCheckMiddleware(BaseMiddleware):
    """Middleware для проверки регистрации пользователя."""
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем user_repository из data (инъектируется DependencyInjectionMiddleware)
        user_repository = data.get("user_repository")
        if user_repository is None:
            raise ValueError("UserRepository не инициализирован в middleware")

        user_id = event.from_user.id

        # Разрешить команду /start и связанные с регистрацией callback/сообщения
        if isinstance(event, Message) and (
            event.text == "/start"
            or data.get("fsm_state") == "RegistrationStates:waiting_for_description"
        ):
            return await handler(event, data)
        elif isinstance(event, CallbackQuery) and (
            event.data == "register_request" or event.data.startswith("admin_")
        ):
            return await handler(event, data)

        if user_id in config.admin_ids:
            return await handler(event, data)

        user = await user_repository.get_by_telegram_id(user_id)

        if user and user.is_registered:
            return await handler(event, data)
        else:
            if isinstance(event, Message):
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Зарегистрироваться",
                                callback_data="register_request",
                            )
                        ]
                    ]
                )
                await event.answer(
                    "Для использования бота вам необходимо зарегистрироваться.",
                    reply_markup=keyboard,
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "Для использования бота вам необходимо зарегистрироваться.",
                    show_alert=True,
                )
            return
```

### Шаг 6: Обновить handlers для использования DI

**Пример для registration.py:**

```python
# src/infrastructure/web/handlers/registration.py
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.configs.config import config
from src.application.use_cases.registration import RegistrationUseCase
from src.application.repositories import IUserRepository

logger = logging.getLogger(__name__)

router = Router()

ADMIN_IDS = config.admin_ids


def get_main_menu() -> ReplyKeyboardMarkup:
    """Создает главное меню с кнопками для зарегистрированных пользователей."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🏋️ Начать тренировку"),
                KeyboardButton(text="✅ Завершить тренировку"),
            ],
            [
                KeyboardButton(text="📝 Записать подход"),
                KeyboardButton(text="💪 Тренажеры"),
            ],
            [
                KeyboardButton(text="📊 Google Sheets"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие из меню",
    )
    return keyboard


class RegistrationStates(StatesGroup):
    waiting_for_description = State()


@router.message(Command("start"))
async def cmd_start(
    message: Message,
    state: FSMContext,
    user_repository: IUserRepository,  # ← Инъекция через middleware
) -> None:
    try:
        user_telegram_id = message.from_user.id
        user = await user_repository.get_by_telegram_id(user_telegram_id)

        if user and user.is_registered:
            logger.info(f"Пользователь {user_telegram_id} уже зарегистрирован и использовал /start.")
            await message.answer(
                f"С возвращением, {message.from_user.full_name}! Вы уже зарегистрированы.",
                reply_markup=get_main_menu(),
            )
        elif user and not user.is_registered:
            logger.info(f"Пользователь {user_telegram_id} ожидает одобрения администратора и использовал /start.")
            await message.answer("Ваш запрос на регистрацию ожидает одобрения администратором.")
        else:
            logger.info(f"Новый пользователь {user_telegram_id} использовал /start. Запрос на регистрацию.")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Зарегистрироваться", callback_data="register_request")]
            ])
            await message.answer(
                f"Привет, {message.from_user.full_name}! Я бот для логирования тренировок. Чтобы начать, пожалуйста, зарегистрируйтесь.",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка в cmd_start для пользователя {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке команды /start.")


# ... остальные handlers аналогично - добавить параметры с типами для инъекции
```

### Шаг 7: Тестирование

```bash
# Запустить бота
uv run python -m src.main

# Проверить что:
# 1. Бот запускается без ошибок
# 2. Можно зарегистрироваться
# 3. Можно начать тренировку
# 4. Можно добавить тренажёр
```

### Шаг 8: Закоммитить изменения

```bash
git add .
git commit -m "feat: Implement DI container with dependency-injector (TASK-001)

- Add dependency-injector to project
- Create Container with all dependencies
- Implement DependencyInjectionMiddleware
- Refactor main.py to use container
- Update handlers to receive dependencies via parameters
- Remove all global variables and type: ignore
- Remove ruff: noqa: F821 from handlers

Breaking changes: None (internal refactoring)
Tests: Manual testing passed
"
```

---

## 📝 TASK-002: Исправить управление сессиями (День 4-5)

### Проблема
Сейчас сессия создаётся один раз и сразу закрывается:
```python
async for session in get_session():
    # ...
    break  # ❌ Закрываем сессию!
```

### Решение: Session per Request

### Шаг 1: Обновить session.py

```python
# src/infrastructure/db/base.py
import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.configs.config import config

logger = logging.getLogger(__name__)

# Создаём engine один раз
engine = create_async_engine(
    config.database_url,
    echo=False,  # Отключить в production
    pool_pre_ping=True,  # Проверять соединение перед использованием
    pool_size=10,  # Размер пула
    max_overflow=20,  # Максимальное количество доп. соединений
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session():
    """Context manager для создания и управления сессией БД.
    
    Yields:
        AsyncSession: Сессия SQLAlchemy
        
    Example:
        async with get_session() as session:
            # работа с сессией
            await session.commit()
    """
    session: AsyncSession = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Database session rollback due to exception")
        raise
    finally:
        await session.close()


async def init_db():
    """Инициализация базы данных (создание таблиц)."""
    from src.domain.models import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def close_db():
    """Закрытие всех соединений с БД."""
    await engine.dispose()
    logger.info("Database connections closed")
```

### Шаг 2: Создать Database Middleware

```bash
touch src/infrastructure/web/middlewares/database.py
```

```python
# src/infrastructure/web/middlewares/database.py
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.base import get_session

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для управления сессиями БД.
    
    Создаёт новую сессию для каждого запроса и автоматически
    делает commit при успехе или rollback при ошибке.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with get_session() as session:
            # Инъектируем сессию в data
            data["db_session"] = session
            
            try:
                result = await handler(event, data)
                # Commit автоматически происходит в context manager
                return result
            except Exception as e:
                # Rollback автоматически происходит в context manager
                logger.error(f"Error in handler: {e}", exc_info=True)
                raise
```

### Шаг 3: Обновить Container

```python
# src/container.py (изменения)
class Container(containers.DeclarativeContainer):
    """Контейнер зависимостей приложения."""

    # ... остальное без изменений ...

    # Repositories теперь принимают сессию как параметр
    # (сессия будет передаваться через middleware)
    
    @staticmethod
    def user_repository(session: AsyncSession) -> UserRepository:
        return UserRepository(session)
    
    @staticmethod
    def machine_repository(session: AsyncSession) -> MachineRepository:
        return MachineRepository(session)
    
    # ... и так далее для всех репозиториев ...
```

### Шаг 4: Обновить DependencyInjectionMiddleware

```python
# src/infrastructure/web/middlewares/dependency_injection.py
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from src.container import Container


class DependencyInjectionMiddleware(BaseMiddleware):
    """Middleware для инъекции зависимостей в handlers."""

    def __init__(self, container: Container):
        self.container = container
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем сессию из data (инъектируется DatabaseMiddleware)
        session: AsyncSession = data.get("db_session")
        if session is None:
            raise ValueError("Database session not found in middleware data")
        
        # Создаём репозитории с текущей сессией
        user_repo = self.container.user_repository(session)
        machine_repo = self.container.machine_repository(session)
        muscle_repo = self.container.muscle_repository(session)
        workout_session_repo = self.container.workout_session_repository(session)
        set_entry_repo = self.container.set_entry_repository(session)
        
        # Инъецируем use cases в data
        data["registration_use_case"] = self.container.registration_use_case(user_repo)
        data["workout_use_case"] = self.container.workout_use_case(
            workout_session_repo, set_entry_repo, machine_repo
        )
        data["machine_management_use_case"] = self.container.machine_management_use_case(
            machine_repo, muscle_repo
        )
        data["google_sheets_export_use_case"] = self.container.google_sheets_export_use_case(
            user_repo, machine_repo, set_entry_repo
        )
        data["muscle_repository"] = muscle_repo
        data["user_repository"] = user_repo

        return await handler(event, data)
```

### Шаг 5: Обновить main.py

```python
# src/main.py (добавить DatabaseMiddleware)
from src.infrastructure.web.middlewares.database import DatabaseMiddleware

async def main() -> None:
    # ... инициализация ...
    
    # Регистрация middleware (порядок ОЧЕНЬ важен!)
    # 1. Database (создаёт сессию)
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    # 2. Dependency Injection (использует сессию из DatabaseMiddleware)
    dp.message.middleware(DependencyInjectionMiddleware(container))
    dp.callback_query.middleware(DependencyInjectionMiddleware(container))
    
    # 3. Registration Check
    registration_check_middleware = RegistrationCheckMiddleware()
    dp.message.middleware(registration_check_middleware)
    dp.callback_query.middleware(registration_check_middleware)
    
    # ... остальное ...
```

### Шаг 6: Удалить commit() из репозиториев

```python
# src/infrastructure/db/repositories/machine_repository.py (пример)
class MachineRepository(IMachineRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, machine: Machine) -> Machine:
        try:
            self.session.add(machine)
            await self.session.flush()  # ← Используем flush вместо commit
            await self.session.refresh(machine)
            logger.info(f"Добавлен новый тренажёр {machine.id}")
            return machine
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError при добавлении тренажёра: {e}", exc_info=True)
            raise  # ← Не делаем rollback, это сделает middleware

    async def update(self, machine: Machine) -> Machine:
        try:
            await self.session.flush()  # ← flush вместо commit
            await self.session.refresh(machine)
            logger.info(f"Обновлён тренажёр {machine.id}.")
            return machine
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError при обновлении тренажёра {machine.id}: {e}", exc_info=True)
            raise

    # ... остальные методы аналогично ...
```

### Шаг 7: Тестирование

```bash
# Запустить бота
uv run python -m src.main

# Тестировать:
# 1. Создание тренажёра
# 2. Начало тренировки
# 3. Запись подхода
# 4. Намеренно вызвать ошибку и проверить rollback
```

### Шаг 8: Закоммитить

```bash
git add .
git commit -m "feat: Implement proper session management (TASK-002)

- Create DatabaseMiddleware for session per request
- Update repositories to use flush() instead of commit()
- Add proper transaction management
- Remove broken async for session in get_session(): break pattern
- Add connection pooling settings

Breaking changes: None
Tests: Manual testing passed
Related: TASK-001
"
```

---

## ⚡ Быстрый чек-лист

После выполнения TASK-001 и TASK-002:

- [ ] Нет глобальных переменных в main.py
- [ ] Нет `# type: ignore` в handlers
- [ ] Нет `# ruff: noqa: F821` в handlers
- [ ] Container определён и используется
- [ ] DatabaseMiddleware создаёт сессию для каждого запроса
- [ ] DependencyInjectionMiddleware инъектирует зависимости
- [ ] Репозитории используют flush() вместо commit()
- [ ] Все handlers получают зависимости через параметры
- [ ] Бот запускается и работает корректно

---

## 🎯 Что дальше?

После выполнения критических задач:

1. **TASK-003** - Транзакционное управление
2. **TASK-004** - Убрать прямой доступ к репозиториям
3. **TASK-007** - Идемпотентность
4. **TASK-008** - Graceful shutdown

Подробнее см. **TASKS.md**

---

## 📚 Полезные ссылки

- [dependency-injector docs](https://python-dependency-injector.ets-labs.org/)
- [SQLAlchemy async](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
- [aiogram middleware](https://docs.aiogram.dev/en/latest/dispatcher/middlewares.html)

---

**Удачи! 🚀**
