#!/usr/bin/env python3
"""
Скрипт для идемпотентного заполнения базы данных мышцами и мышечными зонами из YAML-справочника.

Автоматически создаёт SSH туннель к удалённой БД, если DATABASE_URL указывает на localhost:5433.
Скрипт полностью идемпотентен: не создаёт дубликаты, удаляет данные которых нет в справочнике
(с проверкой использования в других таблицах).
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import yaml
from dotenv import load_dotenv
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Загружаем .env_admin ПЕРЕД импортом config, чтобы DATABASE_URL был правильным
env_admin_path = project_root / ".env_admin"
if env_admin_path.exists():
    load_dotenv(dotenv_path=env_admin_path, override=True)

from src.configs.logging_config import setup_logging
from src.infrastructure.db.base import get_session
from src.infrastructure.db.repositories.muscle_repository import MuscleRepository
from src.domain.models import (
    MuscleZone,
    Muscle,
    MuscleZoneMuscle,
    MachineZone,
    MachineMuscle,
    MachineLibraryZone,
    MachineLibraryMuscle,
    SetEntryZone,
    SetEntryMuscle,
)

# Импорт из scripts (относительный импорт)
from ssh_tunnel import ssh_tunnel_from_config

setup_logging()
logger = logging.getLogger(__name__)

if env_admin_path.exists():
    logger.info(f"Загружен .env_admin из {env_admin_path}")
else:
    logger.warning(f"Файл .env_admin не найден: {env_admin_path}")


def parse_reference_file(file_path: Path) -> Dict[str, List[str]]:
    """
    Парсит YAML-справочник muscle_reference_zones_muscles.yaml
    и возвращает словарь {зона: [список мышц]}.
    
    Args:
        file_path: Путь к YAML файлу
        
    Returns:
        Словарь {название_зоны: [список_названий_мышц]}
        
    Raises:
        ValueError: Если структура YAML некорректна
        FileNotFoundError: Если файл не найден
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Файл справочника не найден: {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Ошибка парсинга YAML: {e}") from e
    
    if not isinstance(data, dict):
        raise ValueError("YAML файл должен содержать словарь")
    
    if "muscle_zones" not in data:
        raise ValueError("YAML файл должен содержать ключ 'muscle_zones'")
    
    zones_muscles: Dict[str, List[str]] = {}
    
    for zone_entry in data["muscle_zones"]:
        if not isinstance(zone_entry, dict):
            raise ValueError("Каждая запись в muscle_zones должна быть словарём")
        
        if "zone" not in zone_entry:
            raise ValueError("Каждая запись должна содержать ключ 'zone'")
        
        zone_name = str(zone_entry["zone"]).strip()
        if not zone_name:
            raise ValueError("Название зоны не может быть пустым")
        
        muscles = zone_entry.get("muscles", [])
        if not isinstance(muscles, list):
            raise ValueError(f"Мышцы для зоны '{zone_name}' должны быть списком")
        
        muscle_names = [str(m).strip() for m in muscles if m]
        if not muscle_names:
            logger.warning(f"Зона '{zone_name}' не содержит мышц")
        
        zones_muscles[zone_name] = muscle_names
    
    if not zones_muscles:
        raise ValueError("В справочнике не найдено ни одной зоны")
    
    return zones_muscles


def _unique_ordered(items: List[str]) -> List[str]:
    """Удаляет дубликаты, сохраняя порядок."""
    seen = set()
    result: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


async def check_zone_usage(session: AsyncSession, zone_id: int) -> bool:
    """
    Проверяет, используется ли зона в других таблицах.
    
    Returns:
        True если зона используется, False если можно удалить
    """
    # Проверяем machine_zones
    stmt = select(func.count()).select_from(MachineZone).where(MachineZone.zone_id == zone_id)
    result = await session.execute(stmt)
    if result.scalar() > 0:
        return True
    
    # Проверяем machine_library_zones
    stmt = select(func.count()).select_from(MachineLibraryZone).where(
        MachineLibraryZone.zone_id == zone_id
    )
    result = await session.execute(stmt)
    if result.scalar() > 0:
        return True
    
    # Проверяем set_entry_zones
    stmt = select(func.count()).select_from(SetEntryZone).where(SetEntryZone.zone_id == zone_id)
    result = await session.execute(stmt)
    if result.scalar() > 0:
        return True
    
    return False


async def check_muscle_usage(session: AsyncSession, muscle_id: int) -> bool:
    """
    Проверяет, используется ли мышца в других таблицах.
    
    Returns:
        True если мышца используется, False если можно удалить
    """
    # Проверяем machine_muscles
    stmt = select(func.count()).select_from(MachineMuscle).where(
        MachineMuscle.muscle_id == muscle_id
    )
    result = await session.execute(stmt)
    if result.scalar() > 0:
        return True
    
    # Проверяем machine_library_muscles
    stmt = select(func.count()).select_from(MachineLibraryMuscle).where(
        MachineLibraryMuscle.muscle_id == muscle_id
    )
    result = await session.execute(stmt)
    if result.scalar() > 0:
        return True
    
    # Проверяем set_entry_muscles
    stmt = select(func.count()).select_from(SetEntryMuscle).where(
        SetEntryMuscle.muscle_id == muscle_id
    )
    result = await session.execute(stmt)
    if result.scalar() > 0:
        return True
    
    return False


async def seed_muscles() -> None:
    """
    Идемпотентно заполняет базу данных мышцами и зонами из YAML-справочника.
    
    Алгоритм:
    1. Загружает данные из YAML
    2. Получает все существующие зоны, мышцы и связи из БД
    3. Добавляет недостающие зоны/мышцы/связи
    4. Удаляет зоны/мышцы/связи, которых нет в YAML (с проверкой использования)
    """
    reference_file = project_root / "docs" / "db" / "muscle_reference_zones_muscles.yaml"
    
    if not reference_file.exists():
        logger.error(f"Файл {reference_file} не найден!")
        return
    
    # Парсим YAML
    try:
        zones_muscles = parse_reference_file(reference_file)
    except Exception as e:
        logger.error(f"Ошибка при парсинге справочника: {e}", exc_info=True)
        return
    
    # Получаем уникальные мышцы из всех зон
    all_muscle_names = _unique_ordered(
        [muscle for muscles in zones_muscles.values() for muscle in muscles]
    )
    
    logger.info(
        f"Загружено из справочника: {len(zones_muscles)} зон, {len(all_muscle_names)} уникальных мышц"
    )
    
    async with get_session() as session:
        muscle_repo = MuscleRepository(session)
        
        # Получаем существующие данные из БД
        existing_zones = await muscle_repo.get_all_muscle_zones()
        existing_muscles = await muscle_repo.get_all_muscles()
        
        existing_zone_names = {zone.name: zone.id for zone in existing_zones}
        existing_muscle_names = {muscle.name: muscle.id for muscle in existing_muscles}
        
        # Получаем существующие связи
        stmt = select(MuscleZoneMuscle.zone_id, MuscleZoneMuscle.muscle_id)
        result = await session.execute(stmt)
        existing_links: Set[Tuple[int, int]] = set(result.all())
        
        # Статистика операций
        stats = {
            "zones_added": 0,
            "zones_deleted": 0,
            "zones_skipped_deletion": 0,
            "muscles_added": 0,
            "muscles_deleted": 0,
            "muscles_skipped_deletion": 0,
            "links_added": 0,
            "links_deleted": 0,
        }
        
        # === ШАГ 1: Добавляем недостающие зоны ===
        logger.info("Добавление недостающих зон...")
        for zone_name in zones_muscles.keys():
            if zone_name not in existing_zone_names:
                new_zone = MuscleZone(name=zone_name)
                created_zone = await muscle_repo.add_muscle_zone(new_zone)
                existing_zone_names[zone_name] = created_zone.id
                stats["zones_added"] += 1
                logger.info(f"  ✓ Добавлена зона '{zone_name}' (ID: {created_zone.id})")
            else:
                logger.debug(f"  - Зона '{zone_name}' уже существует (ID: {existing_zone_names[zone_name]})")
        
        # === ШАГ 2: Добавляем недостающие мышцы ===
        logger.info("Добавление недостающих мышц...")
        for muscle_name in all_muscle_names:
            if muscle_name not in existing_muscle_names:
                new_muscle = Muscle(name=muscle_name)
                created_muscle = await muscle_repo.add(new_muscle)
                existing_muscle_names[muscle_name] = created_muscle.id
                stats["muscles_added"] += 1
                logger.info(f"  ✓ Добавлена мышца '{muscle_name}' (ID: {created_muscle.id})")
            else:
                logger.debug(
                    f"  - Мышца '{muscle_name}' уже существует (ID: {existing_muscle_names[muscle_name]})"
                )
        
        # === ШАГ 3: Добавляем недостающие связи зона↔мышца ===
        logger.info("Добавление недостающих связей зона↔мышца...")
        for zone_name, muscle_names in zones_muscles.items():
            zone_id = existing_zone_names[zone_name]
            
            for muscle_name in _unique_ordered(muscle_names):
                muscle_id = existing_muscle_names[muscle_name]
                link_key = (zone_id, muscle_id)
                
                if link_key not in existing_links:
                    session.add(MuscleZoneMuscle(zone_id=zone_id, muscle_id=muscle_id))
                    existing_links.add(link_key)
                    stats["links_added"] += 1
                    logger.debug(f"  ✓ Добавлена связь '{zone_name}' → '{muscle_name}'")
        
        # === ШАГ 4: Удаляем связи, которых нет в справочнике ===
        logger.info("Удаление связей, которых нет в справочнике...")
        yaml_zone_names = set(zones_muscles.keys())
        yaml_links: Set[Tuple[int, int]] = set()
        
        for zone_name, muscle_names in zones_muscles.items():
            if zone_name not in existing_zone_names:
                continue
            zone_id = existing_zone_names[zone_name]
            for muscle_name in _unique_ordered(muscle_names):
                if muscle_name not in existing_muscle_names:
                    continue
                muscle_id = existing_muscle_names[muscle_name]
                yaml_links.add((zone_id, muscle_id))
        
        links_to_delete = existing_links - yaml_links
        if links_to_delete:
            # Удаляем все связи
            for zone_id, muscle_id in links_to_delete:
                stmt = delete(MuscleZoneMuscle).where(
                    MuscleZoneMuscle.zone_id == zone_id,
                    MuscleZoneMuscle.muscle_id == muscle_id,
                )
                await session.execute(stmt)
            stats["links_deleted"] = len(links_to_delete)
            logger.info(f"  ✓ Удалено связей: {len(links_to_delete)}")
        else:
            logger.debug("  - Нет связей для удаления")
        
        # === ШАГ 5: Удаляем мышцы, которых нет в справочнике (с проверкой использования) ===
        logger.info("Проверка мышц для удаления...")
        yaml_muscle_names = set(all_muscle_names)
        muscles_to_delete = [
            (muscle_id, muscle_name)
            for muscle_name, muscle_id in existing_muscle_names.items()
            if muscle_name not in yaml_muscle_names
        ]
        
        for muscle_id, muscle_name in muscles_to_delete:
            if await check_muscle_usage(session, muscle_id):
                stats["muscles_skipped_deletion"] += 1
                logger.warning(
                    f"  ⚠ Мышца '{muscle_name}' (ID: {muscle_id}) используется в других таблицах, удаление пропущено"
                )
            else:
                stmt = delete(Muscle).where(Muscle.id == muscle_id)
                await session.execute(stmt)
                stats["muscles_deleted"] += 1
                logger.info(f"  ✓ Удалена мышца '{muscle_name}' (ID: {muscle_id})")
        
        # === ШАГ 6: Удаляем зоны, которых нет в справочнике (с проверкой использования) ===
        logger.info("Проверка зон для удаления...")
        zones_to_delete = [
            (zone_id, zone_name)
            for zone_name, zone_id in existing_zone_names.items()
            if zone_name not in yaml_zone_names
        ]
        
        for zone_id, zone_name in zones_to_delete:
            if await check_zone_usage(session, zone_id):
                stats["zones_skipped_deletion"] += 1
                logger.warning(
                    f"  ⚠ Зона '{zone_name}' (ID: {zone_id}) используется в других таблицах, удаление пропущено"
                )
            else:
                stmt = delete(MuscleZone).where(MuscleZone.id == zone_id)
                await session.execute(stmt)
                stats["zones_deleted"] += 1
                logger.info(f"  ✓ Удалена зона '{zone_name}' (ID: {zone_id})")
        
        # Выводим итоговую статистику
        logger.info("=" * 60)
        logger.info("ИТОГОВАЯ СТАТИСТИКА:")
        logger.info(f"  Зоны: добавлено {stats['zones_added']}, удалено {stats['zones_deleted']}, пропущено удаление {stats['zones_skipped_deletion']}")
        logger.info(f"  Мышцы: добавлено {stats['muscles_added']}, удалено {stats['muscles_deleted']}, пропущено удаление {stats['muscles_skipped_deletion']}")
        logger.info(f"  Связи: добавлено {stats['links_added']}, удалено {stats['links_deleted']}")
        logger.info("=" * 60)
        logger.info("✅ Заполнение базы данных завершено успешно!")


def check_port_available(host: str, port: int) -> bool:
    """Проверяет, доступен ли порт для подключения."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


async def main() -> None:
    """Главная функция с поддержкой SSH туннеля."""
    # Проверяем, нужен ли SSH туннель
    database_url = os.getenv("DATABASE_URL", "")
    use_ssh_tunnel = False
    tunnel_already_up = False
    
    if database_url:
        # Если DATABASE_URL указывает на localhost:5433, проверяем нужен ли туннель
        if "localhost:5433" in database_url or "127.0.0.1:5433" in database_url:
            # Проверяем, доступен ли уже порт (туннель может быть уже поднят)
            if check_port_available("127.0.0.1", 5433):
                logger.info("🔌 Порт 5433 уже доступен, туннель, вероятно, уже поднят")
                tunnel_already_up = True
            else:
                use_ssh_tunnel = True
                logger.info("🔌 Обнаружен DATABASE_URL с localhost:5433, будет создан SSH туннель")
    
    if use_ssh_tunnel:
        # Используем SSH туннель из конфига
        ssh_host = os.getenv("SSH_TUNNEL_HOST", "asgef_fvds_db-tunnel")
        logger.info(f"🔌 Создание SSH туннеля: {ssh_host}")
        
        with ssh_tunnel_from_config(ssh_config_host=ssh_host):
            await seed_muscles()
    else:
        # Прямое подключение (локальная БД или уже настроенный туннель)
        if tunnel_already_up:
            logger.info("🔌 Используется существующий SSH туннель")
        await seed_muscles()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        sys.exit(1)
