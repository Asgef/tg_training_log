#!/usr/bin/env python3
"""
Скрипт для удаления дубликата тренажёра из библиотеки machine_library.

Использование:
    uv run python scripts/delete_machine_library_duplicate.py "Сведение рук (пек дек)"
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Загружаем .env_admin ПЕРЕД импортом config
env_admin_path = project_root / ".env_admin"
if env_admin_path.exists():
    load_dotenv(dotenv_path=env_admin_path, override=True)

from src.configs.logging_config import setup_logging
from src.infrastructure.db.base import get_session
from src.domain.models import MachineLibrary, Machine

setup_logging()
logger = logging.getLogger(__name__)

if env_admin_path.exists():
    logger.info(f"Загружен .env_admin из {env_admin_path}")
else:
    logger.warning(f"Файл .env_admin не найден: {env_admin_path}")


async def check_machine_library_usage(session: AsyncSession, machine_id: int) -> bool:
    """Проверяет, используется ли библиотечный тренажёр пользователями."""
    stmt = select(func.count()).select_from(Machine).where(
        Machine.library_machine_id == machine_id
    )
    result = await session.execute(stmt)
    return result.scalar() > 0


async def delete_machine_library_by_name(name: str) -> None:
    """Удаляет тренажёр из библиотеки по названию."""
    async with get_session() as session:
        try:
            # Ищем тренажёр по названию
            stmt = select(MachineLibrary).where(MachineLibrary.name_ru == name)
            result = await session.execute(stmt)
            machine = result.scalar_one_or_none()
            
            if not machine:
                logger.warning(f"Тренажёр '{name}' не найден в базе данных")
                return
            
            machine_id = machine.id
            logger.info(f"Найден тренажёр '{name}' с ID: {machine_id}")
            
            # Проверяем, используется ли он пользователями
            if await check_machine_library_usage(session, machine_id):
                logger.error(
                    f"⚠ Тренажёр '{name}' (ID: {machine_id}) используется пользователями, "
                    "удаление невозможно!"
                )
                return
            
            # Удаляем тренажёр
            stmt = delete(MachineLibrary).where(MachineLibrary.id == machine_id)
            await session.execute(stmt)
            await session.commit()
            
            logger.info(f"✓ Тренажёр '{name}' (ID: {machine_id}) успешно удалён из библиотеки")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при удалении тренажёра '{name}': {e}", exc_info=True)
            raise


async def main() -> None:
    """Главная функция."""
    if len(sys.argv) < 2:
        logger.error("Использование: python scripts/delete_machine_library_duplicate.py \"Название тренажёра\"")
        sys.exit(1)
    
    name = sys.argv[1].strip()
    if not name:
        logger.error("Название тренажёра не может быть пустым")
        sys.exit(1)
    
    logger.info(f"Попытка удалить тренажёр: '{name}'")
    await delete_machine_library_by_name(name)


if __name__ == "__main__":
    asyncio.run(main())
