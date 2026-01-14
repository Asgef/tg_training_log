from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection

from alembic import context

import sys
import asyncio
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.configs.config import config as app_config

# это объект конфигурации Alembic, который предоставляет
# доступ к значениям в используемом .ini файле.
config = context.config

# Интерпретация конфигурационного файла для логирования Python.
# Эта строка в основном настраивает логгеры.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# добавьте объект MetaData вашей модели здесь
# для поддержки 'autogenerate'
from src.domain.models import Base  # noqa: E402

target_metadata = Base.metadata

# другие значения из конфига, определённые потребностями env.py,
# могут быть получены:
# my_important_option = config.get_main_option("my_important_option")
# ... и т.д.


def run_migrations_offline() -> None:
    """Запуск миграций в 'offline' режиме.

    Это настраивает контекст только с URL
    и без Engine, хотя Engine здесь тоже допустим.
    Пропуская создание Engine,
    нам даже не нужен доступный DBAPI.

    Вызовы context.execute() здесь выводят данную строку в
    вывод скрипта.

    """
    url = app_config.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: AsyncConnection) -> None:
    """Выполняет миграции с использованием async соединения."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Запуск миграций в 'online' режиме с async engine."""
    connectable = create_async_engine(
        app_config.database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск миграций в 'online' режиме."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
