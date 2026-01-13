import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    logger.error(
        "Переменная окружения DATABASE_URL не установлена. Подключение к базе данных не удастся."
    )
    # В реальном приложении стоит поднять ошибку или завершить работу здесь

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


async def get_session() -> AsyncSession:
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except OperationalError as e:
        logger.error(f"Операционная ошибка базы данных: {e}")
        raise
    except Exception as e:
        logger.error(f"Произошла неожиданная ошибка во время сессии базы данных: {e}")
        raise
