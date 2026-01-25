#!/usr/bin/env python3
"""
Скрипт для переноса пользовательских тренажёров с одного библиотечного на другой.

Использование:
    uv run python scripts/migrate_machine_library.py "Сведение рук(пек-дек)" "Сведение рук (Pec deck)"
"""
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select, update
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
from src.domain.models import MachineLibrary, Machine

setup_logging()
logger = logging.getLogger(__name__)


async def migrate_machine_library(from_name: str, to_name: str) -> None:
    """Переносит пользовательские тренажёры с одного библиотечного на другой."""
    async with get_session() as session:
        try:
            # Находим исходный тренажёр
            stmt = select(MachineLibrary).where(MachineLibrary.name_ru == from_name)
            result = await session.execute(stmt)
            from_machine = result.scalar_one_or_none()
            
            if not from_machine:
                logger.error(f"Исходный тренажёр '{from_name}' не найден")
                return
            
            # Находим целевой тренажёр
            stmt = select(MachineLibrary).where(MachineLibrary.name_ru == to_name)
            result = await session.execute(stmt)
            to_machine = result.scalar_one_or_none()
            
            if not to_machine:
                logger.error(f"Целевой тренажёр '{to_name}' не найден")
                return
            
            logger.info(f"Исходный тренажёр: ID {from_machine.id} - '{from_name}'")
            logger.info(f"Целевой тренажёр: ID {to_machine.id} - '{to_name}'")
            
            # Подсчитываем количество пользовательских тренажёров для переноса
            stmt = select(Machine).where(Machine.library_machine_id == from_machine.id)
            result = await session.execute(stmt)
            machines = result.scalars().all()
            
            count = len(machines)
            logger.info(f"Найдено пользовательских тренажёров для переноса: {count}")
            
            if count == 0:
                logger.info("Нет пользовательских тренажёров для переноса")
                return
            
            # Переносим пользовательские тренажёры
            stmt = update(Machine).where(
                Machine.library_machine_id == from_machine.id
            ).values(library_machine_id=to_machine.id)
            
            result = await session.execute(stmt)
            await session.commit()
            
            logger.info(f"✓ Успешно перенесено {result.rowcount} пользовательских тренажёров")
            logger.info(f"Теперь можно удалить исходный тренажёр '{from_name}' (ID: {from_machine.id})")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при переносе: {e}", exc_info=True)
            raise


async def main() -> None:
    """Главная функция."""
    if len(sys.argv) < 3:
        logger.error(
            "Использование: python scripts/migrate_machine_library.py "
            '"Исходное название" "Целевое название"'
        )
        sys.exit(1)
    
    from_name = sys.argv[1].strip()
    to_name = sys.argv[2].strip()
    
    logger.info(f"Перенос с '{from_name}' на '{to_name}'")
    await migrate_machine_library(from_name, to_name)


if __name__ == "__main__":
    asyncio.run(main())
