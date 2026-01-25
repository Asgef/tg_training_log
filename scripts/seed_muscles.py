#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных мышцами и мышечными зонами из YAML-справочника.

Автоматически создаёт SSH туннель к удалённой БД, если DATABASE_URL указывает на localhost:5433.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Iterable, Tuple

from sqlalchemy import select

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.configs.logging_config import setup_logging
from src.infrastructure.db.base import get_session
from src.infrastructure.db.repositories.muscle_repository import MuscleRepository
from src.domain.models import MuscleZone, Muscle, MuscleZoneMuscle

# Импорт из scripts (относительный импорт)
from ssh_tunnel import ssh_tunnel_from_config

setup_logging()
logger = logging.getLogger(__name__)


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value.strip()


def parse_reference_file(file_path: Path) -> Dict[str, List[str]]:
    """
    Парсит YAML-справочник muscle_reference_zones_muscles.yaml
    и возвращает словарь {зона: [список мышц]}.
    """
    zones_muscles: Dict[str, List[str]] = {}
    current_zone: str | None = None
    in_muscles = False

    with open(file_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            if line.startswith("  - zone:"):
                zone_value = line.split(":", 1)[1].strip()
                current_zone = _strip_quotes(zone_value)
                zones_muscles.setdefault(current_zone, [])
                in_muscles = False
                continue

            if stripped == "muscles:":
                if current_zone is None:
                    raise ValueError("Раздел muscles найден до объявления зоны")
                in_muscles = True
                continue

            if in_muscles and line.startswith("      - "):
                muscle_value = line.split("-", 1)[1].strip()
                muscle_name = _strip_quotes(muscle_value)
                if muscle_name:
                    zones_muscles[current_zone].append(muscle_name)
                continue

    if not zones_muscles:
        raise ValueError("В справочнике не найдено ни одной зоны/мышцы")

    return zones_muscles


def _unique_ordered(items: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


async def seed_muscles() -> None:
    """Заполняет базу данных мышцами и зонами"""
    reference_file = project_root / "docs" / "db" / "muscle_reference_zones_muscles.yaml"
    
    if not reference_file.exists():
        logger.error(f"Файл {reference_file} не найден!")
        return
    
    zones_muscles = parse_reference_file(reference_file)
    total_muscles = sum(len(_unique_ordered(muscles)) for muscles in zones_muscles.values())
    logger.info(f"Найдено {len(zones_muscles)} зон, всего {total_muscles} мышц")
    
    async with get_session() as session:
        muscle_repo = MuscleRepository(session)
        
        # Создаем зоны
        existing_zones = await muscle_repo.get_all_muscle_zones()
        zone_id_map: Dict[str, int] = {zone.name: zone.id for zone in existing_zones}

        for zone_name in zones_muscles.keys():
            if zone_name in zone_id_map:
                logger.info(f"Зона '{zone_name}' уже существует (ID: {zone_id_map[zone_name]})")
                continue

            new_zone = MuscleZone(name=zone_name)
            created_zone = await muscle_repo.add_muscle_zone(new_zone)
            zone_id_map[zone_name] = created_zone.id
            logger.info(f"Создана зона '{zone_name}' (ID: {created_zone.id})")
        
        # Создаем мышцы и связи с зонами
        all_muscles = await muscle_repo.get_all_muscles()
        muscle_id_map: Dict[str, int] = {muscle.name: muscle.id for muscle in all_muscles}

        links_result = await session.execute(
            select(MuscleZoneMuscle.zone_id, MuscleZoneMuscle.muscle_id)
        )
        existing_links: set[Tuple[int, int]] = set(links_result.all())
        
        for zone_name, muscle_names in zones_muscles.items():
            zone_id = zone_id_map[zone_name]
            
            for muscle_name in _unique_ordered(muscle_names):
                muscle_id = muscle_id_map.get(muscle_name)
                if muscle_id is None:
                    new_muscle = Muscle(name=muscle_name)
                    created_muscle = await muscle_repo.add(new_muscle)
                    muscle_id = created_muscle.id
                    muscle_id_map[muscle_name] = muscle_id
                    logger.info(
                        f"Создана мышца '{muscle_name}' (ID: {muscle_id})"
                    )

                link_key = (zone_id, muscle_id)
                if link_key not in existing_links:
                    session.add(MuscleZoneMuscle(zone_id=zone_id, muscle_id=muscle_id))
                    existing_links.add(link_key)
                    logger.debug(
                        f"Создана связь зона↔мышца '{zone_name}' → '{muscle_name}'"
                    )
        
        logger.info("Заполнение базы данных завершено успешно!")


async def main() -> None:
    """Главная функция с поддержкой SSH туннеля."""
    # Проверяем, нужен ли SSH туннель
    database_url = os.getenv("DATABASE_URL", "")
    use_ssh_tunnel = False
    
    if database_url:
        # Если DATABASE_URL указывает на localhost:5433, используем SSH туннель
        if "localhost:5433" in database_url or "127.0.0.1:5433" in database_url:
            use_ssh_tunnel = True
            logger.info("🔌 Обнаружен DATABASE_URL с localhost:5433, будет использован SSH туннель")
    
    if use_ssh_tunnel:
        # Используем SSH туннель из конфига
        ssh_host = os.getenv("SSH_TUNNEL_HOST", "asgef_fvds_db-tunnel")
        logger.info(f"🔌 Использование SSH туннеля: {ssh_host}")
        
        with ssh_tunnel_from_config(ssh_config_host=ssh_host):
            await seed_muscles()
    else:
        # Прямое подключение (локальная БД или уже настроенный туннель)
        await seed_muscles()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
