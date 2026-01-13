import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    logger.error(
        "DATABASE_URL environment variable is not set. Database connection will fail."
    )
    # Consider raising an error or exiting here in a real application

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


async def get_session() -> AsyncSession:
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except OperationalError as e:
        logger.error(f"Database operational error: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during database session: {e}")
        raise
