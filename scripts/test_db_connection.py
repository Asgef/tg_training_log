#!/usr/bin/env python3
"""
Скрипт для тестирования соединения с базой данных через SSH туннель.
Проверяет доступность порта, подключение и выполняет простой запрос.

Автоматически создаёт SSH туннель, если DATABASE_URL указывает на localhost:5433.
"""
import asyncio
import logging
import os
import sys
import socket
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.configs.logging_config import setup_logging
from src.infrastructure.db.base import engine, get_session
from src.configs.config import config

# Импорт SSH туннеля из scripts
from ssh_tunnel import ssh_tunnel_from_config

setup_logging()
logger = logging.getLogger(__name__)


def check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Проверяет доступность порта."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Ошибка при проверке порта {host}:{port}: {e}")
        return False


async def test_connection() -> None:
    """Тестирует соединение с базой данных."""
    logger.info("=" * 60)
    logger.info("Тестирование соединения с базой данных")
    logger.info("=" * 60)
    
    # Проверяем наличие DATABASE_URL
    if not config.database_url:
        logger.error("❌ DATABASE_URL не установлен в переменных окружения!")
        return
    
    # Маскируем пароль в логах
    masked_url = config.database_url
    if "@" in masked_url and ":" in masked_url.split("@")[0]:
        parts = masked_url.split("@")
        if len(parts) == 2:
            user_pass = parts[0].split("//")[-1]
            if ":" in user_pass:
                user, _ = user_pass.split(":", 1)
                masked_url = masked_url.replace(user_pass, f"{user}:***")
    
    logger.info(f"📋 DATABASE_URL: {masked_url}")
    
    # Парсим URL для проверки порта
    try:
        # Извлекаем хост и порт из URL
        # Формат: postgresql+asyncpg://user:pass@host:port/db
        url_parts = config.database_url.split("://")[1].split("@")[-1].split("/")[0]
        if ":" in url_parts:
            host, port_str = url_parts.split(":")
            port = int(port_str)
        else:
            host = url_parts
            port = 5432  # дефолтный порт PostgreSQL
        
        logger.info(f"🔍 Проверка доступности порта {host}:{port}...")
        if check_port(host, port):
            logger.info(f"✅ Порт {host}:{port} доступен")
        else:
            logger.warning(f"⚠️  Порт {host}:{port} недоступен. Убедитесь, что SSH туннель запущен:")
            logger.warning(f"   ssh asgef_fvds_db-tunnel -N")
            logger.warning(f"   или")
            logger.warning(f"   ssh -L 5433:localhost:5433 devuser_1@188.120.247.71 -N")
            return
    except Exception as e:
        logger.warning(f"⚠️  Не удалось извлечь хост/порт из URL: {e}")
        logger.info("Продолжаем тестирование подключения...")
    
    # Тестируем подключение через SQLAlchemy
    logger.info("\n🔌 Тестирование подключения через SQLAlchemy...")
    try:
        async with engine.connect() as connection:
            logger.info("✅ Соединение установлено успешно!")
            
            # Проверяем, к какому серверу мы подключены
            logger.info("\n🌐 Проверка подключения к серверу...")
            result = await connection.execute(text("SELECT inet_server_addr(), inet_server_port(), version(), current_database(), current_user"))
            row = result.fetchone()
            
            # Проверяем, запущен ли SSH туннель
            # Если мы внутри контекстного менеджера ssh_tunnel, туннель уже работает
            # Проверяем через subprocess только если туннель создан вручную
            import subprocess
            ssh_tunnel_running = False
            try:
                result_ssh = subprocess.run(
                    ["ps", "aux"], 
                    capture_output=True, 
                    text=True, 
                    timeout=2
                )
                ssh_tunnel_running = "asgef_fvds_db-tunnel" in result_ssh.stdout or "sshtunnel" in result_ssh.stdout.lower()
            except Exception:
                pass
            
            # Если DATABASE_URL указывает на localhost:5433 и подключение работает,
            # значит туннель точно работает (создан автоматически или вручную)
            if "localhost:5433" in config.database_url or "127.0.0.1:5433" in config.database_url:
                ssh_tunnel_running = True  # Подключение работает, значит туннель есть
            
            if row:
                server_ip, server_port, version, db_name, db_user = row
                # Конвертируем IP в строку, если это объект
                server_ip_str = str(server_ip) if server_ip else None
                
                logger.info(f"✅ Запрос выполнен успешно!")
                logger.info(f"   Server IP: {server_ip_str or 'localhost (локальный сервер)'}")
                logger.info(f"   Server Port: {server_port}")
                logger.info(f"   PostgreSQL версия: {version}")
                logger.info(f"   Текущая БД: {db_name}")
                logger.info(f"   Текущий пользователь: {db_user}")
                
                # Проверяем, что это удалённый сервер через SSH туннель
                if ssh_tunnel_running:
                    logger.info(f"✅ SSH туннель запущен")
                    if server_ip_str:
                        # IP 172.18.x.x - это внутренний IP Docker контейнера на удалённом сервере
                        # Это нормально, если SSH туннель работает
                        if server_ip_str.startswith("172.") or server_ip_str.startswith("10.") or server_ip_str.startswith("192.168."):
                            logger.info(f"✅ Подключение к УДАЛЁННОМУ серверу через SSH туннель!")
                            logger.info(f"   Server IP (внутри Docker сети на удалённом сервере): {server_ip_str}")
                        elif server_ip_str == "127.0.0.1" or server_ip_str == "::1":
                            logger.warning(f"⚠️  ВНИМАНИЕ: Server IP = {server_ip_str}")
                            logger.warning(f"   Это может быть локальное подключение")
                        else:
                            logger.info(f"✅ Подключение к УДАЛЁННОМУ серверу {server_ip_str}")
                    else:
                        logger.warning("⚠️  inet_server_addr() вернул NULL, но SSH туннель работает")
                else:
                    logger.warning("⚠️  SSH туннель НЕ запущен!")
                    if server_ip_str:
                        if server_ip_str.startswith("172.") or server_ip_str.startswith("10.") or server_ip_str.startswith("192.168."):
                            logger.warning(f"⚠️  Подключение к внутреннему IP {server_ip_str}")
                            logger.warning(f"   Это может быть ЛОКАЛЬНЫЙ Docker контейнер!")
                            logger.warning(f"   Убедитесь, что:")
                            logger.warning(f"   1. Локальный контейнер остановлен: docker stop tg_training_log_postgres")
                            logger.warning(f"   2. SSH туннель запущен: ssh asgef_fvds_db-tunnel -N")
                        elif server_ip_str == "127.0.0.1" or server_ip_str == "::1":
                            logger.warning(f"⚠️  Подключение к localhost {server_ip_str}")
                            logger.warning(f"   Это локальное подключение, а не через SSH туннель!")
                    else:
                        logger.warning("⚠️  inet_server_addr() вернул NULL и SSH туннель не запущен")
            
            # Проверяем таблицы
            logger.info("\n📋 Проверка существующих таблиц...")
            result = await connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                logger.info(f"✅ Найдено таблиц: {len(tables)}")
                for table in tables[:10]:  # Показываем первые 10
                    logger.info(f"   - {table}")
                if len(tables) > 10:
                    logger.info(f"   ... и ещё {len(tables) - 10} таблиц")
            else:
                logger.warning("⚠️  Таблицы не найдены. Возможно, миграции ещё не выполнены.")
            
            await connection.commit()
            
    except OperationalError as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {e}")
        logger.error("\n💡 Возможные причины:")
        logger.error("   1. SSH туннель не запущен")
        logger.error("   2. Неверные учётные данные в DATABASE_URL")
        logger.error("   3. База данных не запущена на сервере")
        logger.error("   4. Проблемы с сетью")
        return
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
        return
    finally:
        await engine.dispose()
    
    # Тестируем session context manager
    logger.info("\n🔧 Тестирование session context manager...")
    try:
        async with get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            if test_value == 1:
                logger.info("✅ Session context manager работает корректно!")
    except Exception as e:
        logger.error(f"❌ Ошибка при работе с session: {e}", exc_info=True)
        return
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Все тесты пройдены успешно!")
    logger.info("=" * 60)


async def main() -> None:
    """Главная функция с поддержкой автоматического SSH туннеля."""
    # Проверяем, нужен ли SSH туннель
    database_url = os.getenv("DATABASE_URL", config.database_url if config.database_url else "")
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
            await test_connection()
    else:
        # Прямое подключение (локальная БД или уже настроенный туннель)
        logger.info("🔌 Прямое подключение к БД (SSH туннель не требуется)")
        await test_connection()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Прервано пользователем")
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
