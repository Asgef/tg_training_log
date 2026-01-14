"""Модуль для управления подключением к базе данных.

Предоставляет engine с connection pooling и async context manager для сессий.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import OperationalError

from src.configs.config import config

logger = logging.getLogger(__name__)

if not config.database_url:
    logger.error(
        "Переменная окружения DATABASE_URL не установлена. Подключение к базе данных не удастся."
    )
    # В реальном приложении стоит поднять ошибку или завершить работу здесь

# Создаём engine с connection pooling настройками
engine = create_async_engine(
    config.database_url,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_size=10,  # Размер пула соединений
    max_overflow=20,  # Максимальное количество дополнительных соединений
    pool_recycle=3600,  # Переиспользование соединений через час
    echo=False,  # Отключить SQL логирование (можно включить для отладки)
)

# Создаём session factory с правильными настройками
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Объекты остаются доступными после commit
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager для получения сессии БД.
    
    Правильно управляет жизненным циклом сессии:
    - Создаёт сессию при входе
    - Делает commit при успешном завершении
    - Делает rollback при ошибке
    - Закрывает сессию при выходе
    
    Usage:
        async with get_session() as session:
            # работа с сессией
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            if isinstance(e, OperationalError):
                logger.error(f"Операционная ошибка базы данных: {e}", exc_info=True)
            else:
                logger.error(f"Произошла неожиданная ошибка во время сессии базы данных: {e}", exc_info=True)
            raise
        # Сессия автоматически закроется при выходе из context manager
