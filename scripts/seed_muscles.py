#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных мышцами и группами мышц из muscles.md
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.configs.logging_config import setup_logging
from src.infrastructure.db.base import get_session
from src.infrastructure.db.repositories.muscle_repository import MuscleRepository
from src.domain.models import MuscleZone, Muscle, MuscleZoneMuscle

setup_logging()
logger = logging.getLogger(__name__)


def parse_muscles_file(file_path: Path) -> Dict[str, List[str]]:
    """
    Парсит файл muscles.md и возвращает словарь {группа: [список мышц]}
    """
    groups_muscles: Dict[str, List[str]] = {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Разделяем по группам (строки, заканчивающиеся на ":")
    current_group = None
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Проверяем, является ли строка названием группы (заканчивается на ":")
        if line.endswith(':'):
            current_group = line.rstrip(':').strip()
            if current_group not in groups_muscles:
                groups_muscles[current_group] = []
        # Проверяем, является ли строка мышцей (начинается с "-")
        elif line.startswith('-') and current_group:
            muscle_name = line[1:].strip()
            if muscle_name:
                groups_muscles[current_group].append(muscle_name)
    
    return groups_muscles


async def seed_muscles() -> None:
    """Заполняет базу данных мышцами и зонами"""
    muscles_file = project_root / "muscles.md"
    
    if not muscles_file.exists():
        logger.error(f"Файл {muscles_file} не найден!")
        return
    
    zones_muscles = parse_muscles_file(muscles_file)
    total_muscles = sum(len(muscles) for muscles in zones_muscles.values())
    logger.info(f"Найдено {len(zones_muscles)} зон, всего {total_muscles} мышц")
    
    async with get_session() as session:
        muscle_repo = MuscleRepository(session)
        
        # Создаем зоны
        zone_id_map: Dict[str, int] = {}  # Храним только ID, чтобы избежать проблем с async
        
        for zone_name in zones_muscles.keys():
            # Проверяем, существует ли уже зона
            existing_zones = await muscle_repo.get_all_muscle_zones()
            existing_zone = next(
                (z for z in existing_zones if z.name == zone_name),
                None
            )
            
            if existing_zone:
                # Сохраняем ID сразу, пока объект в сессии
                zone_id = existing_zone.id
                logger.info(f"Зона '{zone_name}' уже существует (ID: {zone_id})")
                zone_id_map[zone_name] = zone_id
            else:
                new_zone = MuscleZone(name=zone_name)
                created_zone = await muscle_repo.add_muscle_zone(new_zone)
                zone_id = created_zone.id  # Сохраняем ID сразу
                logger.info(f"Создана зона '{zone_name}' (ID: {zone_id})")
                zone_id_map[zone_name] = zone_id
        
        # Создаем мышцы и связи с зонами
        all_muscles = await muscle_repo.get_all_muscles()
        existing_muscle_names = {m.name for m in all_muscles}
        
        for zone_name, muscle_names in zones_muscles.items():
            zone_id = zone_id_map[zone_name]  # Используем сохраненный ID
            
            for muscle_name in muscle_names:
                if muscle_name in existing_muscle_names:
                    logger.debug(f"Мышца '{muscle_name}' уже существует, пропускаем")
                    # Связь с зоной может отсутствовать — создаём её
                    existing = next((m for m in all_muscles if m.name == muscle_name), None)
                    if existing:
                        link = await session.execute(
                            select(MuscleZoneMuscle).where(
                                MuscleZoneMuscle.zone_id == zone_id,
                                MuscleZoneMuscle.muscle_id == existing.id,
                            )
                        )
                        if link.scalar_one_or_none() is None:
                            session.add(
                                MuscleZoneMuscle(
                                    zone_id=zone_id,
                                    muscle_id=existing.id,
                                )
                            )
                    continue
                
                new_muscle = Muscle(name=muscle_name)
                created_muscle = await muscle_repo.add(new_muscle)
                existing_muscle_names.add(muscle_name)
                session.add(MuscleZoneMuscle(zone_id=zone_id, muscle_id=created_muscle.id))
                logger.info(
                    f"Создана мышца '{muscle_name}' (ID: {created_muscle.id}) в зоне '{zone_name}'"
                )
        
        logger.info("Заполнение базы данных завершено успешно!")


if __name__ == "__main__":
    try:
        asyncio.run(seed_muscles())
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
