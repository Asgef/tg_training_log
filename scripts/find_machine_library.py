#!/usr/bin/env python3
"""
Скрипт для поиска тренажёров в библиотеке по части названия.

Использование:
    uv run python scripts/find_machine_library.py "Сведение"
"""
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Загружаем .env_admin
env_admin_path = project_root / ".env_admin"
if env_admin_path.exists():
    load_dotenv(dotenv_path=env_admin_path, override=True)

from src.configs.logging_config import setup_logging
from src.infrastructure.db.base import get_session
from src.domain.models import MachineLibrary

setup_logging()
logger = logging.getLogger(__name__)


async def find_machines_by_pattern(pattern: str) -> None:
    """Ищет тренажёры по части названия."""
    async with get_session() as session:
        stmt = select(MachineLibrary).where(MachineLibrary.name_ru.ilike(f"%{pattern}%"))
        result = await session.execute(stmt)
        machines = result.scalars().all()
        
        if not machines:
            logger.info(f"Тренажёры с паттерном '{pattern}' не найдены")
            return
        
        logger.info(f"Найдено тренажёров: {len(machines)}")
        for machine in machines:
            logger.info(f"  ID: {machine.id}, Название: '{machine.name_ru}'")


async def main() -> None:
    """Главная функция."""
    if len(sys.argv) < 2:
        logger.error("Использование: python scripts/find_machine_library.py \"Паттерн\"")
        sys.exit(1)
    
    pattern = sys.argv[1].strip()
    await find_machines_by_pattern(pattern)


if __name__ == "__main__":
    asyncio.run(main())
