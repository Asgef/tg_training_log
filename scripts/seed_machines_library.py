#!/usr/bin/env python3
"""
Скрипт для идемпотентного заполнения базы данных библиотекой тренажёров из YAML-справочника.

Автоматически создаёт SSH туннель к удалённой БД, если DATABASE_URL указывает на localhost:5433.
Скрипт полностью идемпотентен: не создаёт дубликаты, удаляет данные которых нет в справочнике
(с проверкой использования в других таблицах).
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

import yaml
from dotenv import load_dotenv
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Загружаем .env_admin ПЕРЕД импортом config, чтобы DATABASE_URL был правильным
env_admin_path = project_root / ".env_admin"
if env_admin_path.exists():
    load_dotenv(dotenv_path=env_admin_path, override=True)

from src.configs.logging_config import setup_logging
from src.infrastructure.db.base import get_session
from src.infrastructure.db.repositories.machine_library_repository import MachineLibraryRepository
from src.infrastructure.db.repositories.muscle_repository import MuscleRepository
from src.domain.models import (
    MachineLibrary,
    MachineLibraryAlias,
    MachineLibraryZone,
    MachineLibraryMuscle,
    Machine,
    MuscleZone,
    Muscle,
)

# Импорт из scripts (относительный импорт)
from ssh_tunnel import ssh_tunnel_from_config

setup_logging()
logger = logging.getLogger(__name__)

if env_admin_path.exists():
    logger.info(f"Загружен .env_admin из {env_admin_path}")
else:
    logger.warning(f"Файл .env_admin не найден: {env_admin_path}")


def parse_reference_file(file_path: Path) -> List[Dict]:
    """
    Парсит YAML-справочник machines_library.yaml
    и возвращает список тренажёров.
    
    Args:
        file_path: Путь к YAML файлу
        
    Returns:
        Список словарей с данными тренажёров
        
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
    
    if "library_machines" not in data:
        raise ValueError("YAML файл должен содержать ключ 'library_machines'")
    
    machines = []
    seen_names = set()
    
    for machine_entry in data["library_machines"]:
        if not isinstance(machine_entry, dict):
            raise ValueError("Каждая запись в library_machines должна быть словарём")
        
        if "name" not in machine_entry:
            raise ValueError("Каждая запись должна содержать ключ 'name'")
        
        name = str(machine_entry["name"]).strip()
        if not name:
            raise ValueError("Название тренажёра не может быть пустым")
        
        # Проверяем уникальность name в YAML
        if name in seen_names:
            logger.warning(f"Дубликат названия в YAML: '{name}', пропускаем")
            continue
        seen_names.add(name)
        
        key = machine_entry.get("key", "")
        aliases = machine_entry.get("aliases", [])
        if not isinstance(aliases, list):
            raise ValueError(f"Алиасы для '{name}' должны быть списком")
        
        zones = machine_entry.get("zones", [])
        if not isinstance(zones, list):
            raise ValueError(f"Зоны для '{name}' должны быть списком")
        
        muscles = machine_entry.get("muscles", [])
        if not isinstance(muscles, list):
            raise ValueError(f"Мышцы для '{name}' должны быть списком")
        
        machines.append({
            "key": key,
            "name": name,
            "aliases": [str(a).strip() for a in aliases if a],
            "zones": [str(z).strip() for z in zones if z],
            "muscles": [str(m).strip() for m in muscles if m],
        })
    
    if not machines:
        raise ValueError("В справочнике не найдено ни одного тренажёра")
    
    return machines


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


async def check_machine_library_usage(session: AsyncSession, library_id: int) -> bool:
    """
    Проверяет, используется ли библиотечный тренажёр в пользовательских тренажёрах.
    
    Returns:
        True если тренажёр используется, False если можно удалить
    """
    stmt = select(func.count()).select_from(Machine).where(
        Machine.library_machine_id == library_id
    )
    result = await session.execute(stmt)
    return result.scalar() > 0


async def seed_machines_library() -> None:
    """
    Идемпотентно заполняет базу данных библиотекой тренажёров из YAML-справочника.
    
    Алгоритм:
    1. Загружает данные из YAML
    2. Получает все существующие библиотечные тренажёры из БД
    3. Добавляет недостающие тренажёры/алиасы/связи
    4. Удаляет тренажёры/алиасы/связи, которых нет в YAML (с проверкой использования)
    """
    reference_file = project_root / "docs" / "db" / "machines_library.yaml"
    
    if not reference_file.exists():
        logger.error(f"Файл {reference_file} не найден!")
        return
    
    # Парсим YAML
    try:
        yaml_machines = parse_reference_file(reference_file)
    except Exception as e:
        logger.error(f"Ошибка при парсинге справочника: {e}", exc_info=True)
        return
    
    logger.info(f"Загружено из справочника: {len(yaml_machines)} тренажёров")
    
    async with get_session() as session:
        library_repo = MachineLibraryRepository(session)
        muscle_repo = MuscleRepository(session)
        
        # Получаем существующие данные из БД
        existing_machines = await library_repo.list_library_machines(limit=10000, offset=0)
        existing_machine_names = {m.name_ru: m for m in existing_machines}
        
        # Получаем все зоны и мышцы для сопоставления по названиям
        existing_zones = await muscle_repo.get_all_muscle_zones()
        existing_muscles = await muscle_repo.get_all_muscles()
        zone_name_to_id = {zone.name: zone.id for zone in existing_zones}
        muscle_name_to_id = {muscle.name: muscle.id for muscle in existing_muscles}
        
        # Получаем все существующие алиасы
        stmt = select(MachineLibraryAlias)
        result = await session.execute(stmt)
        existing_aliases = {alias.alias: alias for alias in result.scalars().all()}
        
        # Получаем все существующие связи
        stmt_zones = select(MachineLibraryZone.machine_library_id, MachineLibraryZone.zone_id)
        result_zones = await session.execute(stmt_zones)
        existing_zone_links: Set[Tuple[int, int]] = set(result_zones.all())
        
        stmt_muscles = select(MachineLibraryMuscle.machine_library_id, MachineLibraryMuscle.muscle_id)
        result_muscles = await session.execute(stmt_muscles)
        existing_muscle_links: Set[Tuple[int, int]] = set(result_muscles.all())
        
        # Статистика операций
        stats = {
            "machines_added": 0,
            "machines_deleted": 0,
            "machines_skipped_deletion": 0,
            "aliases_added": 0,
            "aliases_deleted": 0,
            "aliases_skipped": 0,
            "zone_links_added": 0,
            "zone_links_deleted": 0,
            "muscle_links_added": 0,
            "muscle_links_deleted": 0,
        }
        
        # === ШАГ 1: Добавляем недостающие тренажёры и обновляем существующие ===
        logger.info("Добавление/обновление тренажёров...")
        yaml_machine_names = set()
        
        for machine_data in yaml_machines:
            name = machine_data["name"]
            yaml_machine_names.add(name)
            
            if name in existing_machine_names:
                # Тренажёр существует - обновляем связи и алиасы
                library_machine = existing_machine_names[name]
                logger.debug(f"  - Тренажёр '{name}' уже существует (ID: {library_machine.id})")
            else:
                # Создаём новый тренажёр
                new_machine = MachineLibrary(name_ru=name)
                library_machine = await library_repo.add(new_machine)
                existing_machine_names[name] = library_machine
                stats["machines_added"] += 1
                logger.info(f"  ✓ Добавлен тренажёр '{name}' (ID: {library_machine.id})")
            
            library_id = library_machine.id
            
            # === ШАГ 2: Обновляем алиасы ===
            yaml_aliases = set(machine_data["aliases"])
            
            # Получаем существующие алиасы для этого тренажёра
            existing_machine_aliases = {
                alias.alias: alias
                for alias in existing_aliases.values()
                if alias.machine_library_id == library_id
            }
            
            # Добавляем новые алиасы
            for alias_name in yaml_aliases:
                if alias_name not in existing_machine_aliases:
                    # Проверяем, не используется ли алиас другим тренажёром
                    if alias_name in existing_aliases:
                        stats["aliases_skipped"] += 1
                        logger.warning(
                            f"  ⚠ Алиас '{alias_name}' уже используется другим тренажёром, пропущен"
                        )
                        continue
                    
                    try:
                        new_alias = MachineLibraryAlias(
                            machine_library_id=library_id, alias=alias_name
                        )
                        session.add(new_alias)
                        existing_aliases[alias_name] = new_alias
                        stats["aliases_added"] += 1
                        logger.debug(f"    ✓ Добавлен алиас '{alias_name}'")
                    except IntegrityError:
                        stats["aliases_skipped"] += 1
                        logger.warning(f"    ⚠ Алиас '{alias_name}' уже существует, пропущен")
            
            # Удаляем алиасы, которых нет в YAML
            aliases_to_delete = set(existing_machine_aliases.keys()) - yaml_aliases
            for alias_name in aliases_to_delete:
                alias_obj = existing_machine_aliases[alias_name]
                stmt = delete(MachineLibraryAlias).where(MachineLibraryAlias.id == alias_obj.id)
                await session.execute(stmt)
                del existing_aliases[alias_name]
                stats["aliases_deleted"] += 1
                logger.debug(f"    ✓ Удалён алиас '{alias_name}'")
            
            # === ШАГ 3: Обновляем связи с зонами ===
            yaml_zone_names = set(machine_data["zones"])
            yaml_zone_links: Set[Tuple[int, int]] = set()
            
            for zone_name in yaml_zone_names:
                if zone_name not in zone_name_to_id:
                    logger.warning(
                        f"  ⚠ Зона '{zone_name}' не найдена в БД для тренажёра '{name}', пропущена"
                    )
                    continue
                zone_id = zone_name_to_id[zone_name]
                yaml_zone_links.add((library_id, zone_id))
            
            # Добавляем новые связи
            for link_key in yaml_zone_links:
                if link_key not in existing_zone_links:
                    session.add(MachineLibraryZone(machine_library_id=link_key[0], zone_id=link_key[1]))
                    existing_zone_links.add(link_key)
                    stats["zone_links_added"] += 1
                    # Находим название зоны для логирования
                    zone_name_for_log = next(
                        (name for name, zid in zone_name_to_id.items() if zid == link_key[1]),
                        f"ID:{link_key[1]}"
                    )
                    logger.debug(f"    ✓ Добавлена связь с зоной '{zone_name_for_log}'")
            
            # Удаляем связи, которых нет в YAML
            machine_zone_links = {
                link for link in existing_zone_links if link[0] == library_id
            }
            zone_links_to_delete = machine_zone_links - yaml_zone_links
            if zone_links_to_delete:
                for link_key in zone_links_to_delete:
                    stmt = delete(MachineLibraryZone).where(
                        MachineLibraryZone.machine_library_id == link_key[0],
                        MachineLibraryZone.zone_id == link_key[1],
                    )
                    await session.execute(stmt)
                    existing_zone_links.discard(link_key)
                stats["zone_links_deleted"] += len(zone_links_to_delete)
                logger.debug(f"    ✓ Удалено связей с зонами: {len(zone_links_to_delete)}")
            
            # === ШАГ 4: Обновляем связи с мышцами ===
            yaml_muscle_names = set(machine_data["muscles"])
            yaml_muscle_links: Set[Tuple[int, int]] = set()
            
            for muscle_name in yaml_muscle_names:
                if muscle_name not in muscle_name_to_id:
                    logger.warning(
                        f"  ⚠ Мышца '{muscle_name}' не найдена в БД для тренажёра '{name}', пропущена"
                    )
                    continue
                muscle_id = muscle_name_to_id[muscle_name]
                yaml_muscle_links.add((library_id, muscle_id))
            
            # Добавляем новые связи
            for link_key in yaml_muscle_links:
                if link_key not in existing_muscle_links:
                    session.add(
                        MachineLibraryMuscle(machine_library_id=link_key[0], muscle_id=link_key[1])
                    )
                    existing_muscle_links.add(link_key)
                    stats["muscle_links_added"] += 1
                    # Находим название мышцы для логирования
                    muscle_name_for_log = next(
                        (name for name, mid in muscle_name_to_id.items() if mid == link_key[1]),
                        f"ID:{link_key[1]}"
                    )
                    logger.debug(f"    ✓ Добавлена связь с мышцей '{muscle_name_for_log}'")
            
            # Удаляем связи, которых нет в YAML
            machine_muscle_links = {
                link for link in existing_muscle_links if link[0] == library_id
            }
            muscle_links_to_delete = machine_muscle_links - yaml_muscle_links
            if muscle_links_to_delete:
                for link_key in muscle_links_to_delete:
                    stmt = delete(MachineLibraryMuscle).where(
                        MachineLibraryMuscle.machine_library_id == link_key[0],
                        MachineLibraryMuscle.muscle_id == link_key[1],
                    )
                    await session.execute(stmt)
                    existing_muscle_links.discard(link_key)
                stats["muscle_links_deleted"] += len(muscle_links_to_delete)
                logger.debug(f"    ✓ Удалено связей с мышцами: {len(muscle_links_to_delete)}")
        
        # === ШАГ 5: Удаляем тренажёры, которых нет в YAML (с проверкой использования) ===
        logger.info("Проверка тренажёров для удаления...")
        machines_to_delete = [
            (machine_id, machine_name)
            for machine_name, machine in existing_machine_names.items()
            if machine_name not in yaml_machine_names
        ]
        
        for machine_id, machine_name in machines_to_delete:
            if await check_machine_library_usage(session, machine_id):
                stats["machines_skipped_deletion"] += 1
                logger.warning(
                    f"  ⚠ Тренажёр '{machine_name}' (ID: {machine_id}) используется пользователями, удаление пропущено"
                )
            else:
                stmt = delete(MachineLibrary).where(MachineLibrary.id == machine_id)
                await session.execute(stmt)
                stats["machines_deleted"] += 1
                logger.info(f"  ✓ Удалён тренажёр '{machine_name}' (ID: {machine_id})")
        
        # Выводим итоговую статистику
        logger.info("=" * 60)
        logger.info("ИТОГОВАЯ СТАТИСТИКА:")
        logger.info(
            f"  Тренажёры: добавлено {stats['machines_added']}, удалено {stats['machines_deleted']}, пропущено удаление {stats['machines_skipped_deletion']}"
        )
        logger.info(
            f"  Алиасы: добавлено {stats['aliases_added']}, удалено {stats['aliases_deleted']}, пропущено {stats['aliases_skipped']}"
        )
        logger.info(
            f"  Связи с зонами: добавлено {stats['zone_links_added']}, удалено {stats['zone_links_deleted']}"
        )
        logger.info(
            f"  Связи с мышцами: добавлено {stats['muscle_links_added']}, удалено {stats['muscle_links_deleted']}"
        )
        logger.info("=" * 60)
        logger.info("✅ Заполнение библиотеки тренажёров завершено успешно!")


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
            await seed_machines_library()
    else:
        # Прямое подключение (локальная БД или уже настроенный туннель)
        if tunnel_already_up:
            logger.info("🔌 Используется существующий SSH туннель")
        await seed_machines_library()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        sys.exit(1)
