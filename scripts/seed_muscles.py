#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных мышцами и группами мышц из muscles.md
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.configs.logging_config import setup_logging
from src.infrastructure.db.base import get_session
from src.infrastructure.db.repositories.muscle_repository import MuscleRepository
from src.domain.models import MuscleGroup, Muscle

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
    """Заполняет базу данных мышцами и группами мышц"""
    muscles_file = project_root / "muscles.md"
    
    if not muscles_file.exists():
        logger.error(f"Файл {muscles_file} не найден!")
        return
    
    groups_muscles = parse_muscles_file(muscles_file)
    total_muscles = sum(len(muscles) for muscles in groups_muscles.values())
    logger.info(f"Найдено {len(groups_muscles)} групп мышц, всего {total_muscles} мышц")
    
    async with get_session() as session:
        muscle_repo = MuscleRepository(session)
        
        # Создаем группы мышц
        group_id_map: Dict[str, int] = {}  # Храним только ID, чтобы избежать проблем с async
        
        for group_name in groups_muscles.keys():
            # Проверяем, существует ли уже группа
            existing_groups = await muscle_repo.get_all_muscle_groups()
            existing_group = next(
                (g for g in existing_groups if g.name == group_name),
                None
            )
            
            if existing_group:
                # Сохраняем ID сразу, пока объект в сессии
                group_id = existing_group.id
                logger.info(f"Группа мышц '{group_name}' уже существует (ID: {group_id})")
                group_id_map[group_name] = group_id
            else:
                new_group = MuscleGroup(name=group_name)
                created_group = await muscle_repo.add_muscle_group(new_group)
                group_id = created_group.id  # Сохраняем ID сразу
                logger.info(f"Создана группа мышц '{group_name}' (ID: {group_id})")
                group_id_map[group_name] = group_id
        
        # Создаем мышцы
        all_muscles = await muscle_repo.get_all_muscles()
        existing_muscle_names = {m.name for m in all_muscles}
        
        for group_name, muscle_names in groups_muscles.items():
            group_id = group_id_map[group_name]  # Используем сохраненный ID
            
            for muscle_name in muscle_names:
                if muscle_name in existing_muscle_names:
                    logger.debug(f"Мышца '{muscle_name}' уже существует, пропускаем")
                    continue
                
                new_muscle = Muscle(name=muscle_name, group_id=group_id)
                created_muscle = await muscle_repo.add(new_muscle)
                existing_muscle_names.add(muscle_name)
                logger.info(f"Создана мышца '{muscle_name}' (ID: {created_muscle.id}) в группе '{group_name}'")
        
        logger.info("Заполнение базы данных завершено успешно!")


if __name__ == "__main__":
    try:
        asyncio.run(seed_muscles())
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
