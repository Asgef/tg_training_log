"""Утилита для автоматического управления SSH туннелем к базе данных.

Предоставляет контекстный менеджер для автоматического создания и закрытия SSH туннеля.
"""
import logging
import os
from contextlib import contextmanager
from typing import Optional

from sshtunnel import SSHTunnelForwarder

logger = logging.getLogger(__name__)


@contextmanager
def ssh_tunnel(
    ssh_host: str,
    ssh_port: int = 22,
    ssh_username: str = "devuser_1",
    ssh_private_key: Optional[str] = None,
    remote_bind_address: tuple[str, int] = ("localhost", 5433),
    local_bind_address: tuple[str, int] = ("127.0.0.1", 5433),
):
    """
    Контекстный менеджер для создания SSH туннеля к удалённой базе данных.
    
    Автоматически создаёт туннель при входе и закрывает при выходе.
    
    Args:
        ssh_host: Хост SSH сервера
        ssh_port: Порт SSH сервера (по умолчанию 22)
        ssh_username: Имя пользователя для SSH
        ssh_private_key: Путь к приватному ключу SSH (если None, используется ~/.ssh/id_rsa)
        remote_bind_address: Адрес и порт на удалённом сервере (host, port)
        local_bind_address: Адрес и порт для локального проброса (host, port)
    
    Yields:
        SSHTunnelForwarder: Объект туннеля (можно использовать для получения local_bind_port)
    
    Example:
        ```python
        with ssh_tunnel(
            ssh_host="188.120.247.71",
            ssh_username="devuser_1",
            ssh_private_key="~/.ssh/projects/asgef_fvds/devuser_1"
        ):
            # Здесь можно подключаться к БД через localhost:5433
            # Туннель автоматически закроется при выходе
            pass
        ```
    """
    # Определяем путь к приватному ключу
    if ssh_private_key is None:
        # Пробуем найти ключ в стандартных местах
        default_key = os.path.expanduser("~/.ssh/id_rsa")
        if os.path.exists(default_key):
            ssh_private_key = default_key
        else:
            raise ValueError(
                "SSH private key не указан и не найден в ~/.ssh/id_rsa. "
                "Укажите ssh_private_key явно."
            )
    
    ssh_private_key = os.path.expanduser(ssh_private_key)
    
    if not os.path.exists(ssh_private_key):
        raise FileNotFoundError(f"SSH private key не найден: {ssh_private_key}")
    
    logger.info(f"🔌 Создание SSH туннеля к {ssh_host}:{ssh_port}...")
    logger.info(f"   Remote: {remote_bind_address[0]}:{remote_bind_address[1]}")
    logger.info(f"   Local: {local_bind_address[0]}:{local_bind_address[1]}")
    
    tunnel = SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=ssh_username,
        ssh_pkey=ssh_private_key,
        remote_bind_address=remote_bind_address,
        local_bind_address=local_bind_address,
        # Дополнительные настройки для надёжности
        set_keepalive=30,  # Keep-alive каждые 30 секунд
        allow_agent=False,  # Отключаем SSH agent для избежания проблем с paramiko
    )
    
    try:
        tunnel.start()
        logger.info(f"✅ SSH туннель создан успешно")
        logger.info(f"   Локальный порт: {tunnel.local_bind_port}")
        yield tunnel
    except Exception as e:
        logger.error(f"❌ Ошибка при создании SSH туннеля: {e}", exc_info=True)
        raise
    finally:
        if tunnel.is_alive:
            logger.info("🔌 Закрытие SSH туннеля...")
            tunnel.stop()
            logger.info("✅ SSH туннель закрыт")


@contextmanager
def ssh_tunnel_from_config(
    ssh_config_host: Optional[str] = None,
    remote_bind_address: tuple[str, int] = ("localhost", 5433),
    local_bind_address: tuple[str, int] = ("127.0.0.1", 5433),
):
    """
    Контекстный менеджер для создания SSH туннеля из SSH config.
    
    Использует настройки из ~/.ssh/config для указанного хоста.
    
    Args:
        ssh_config_host: Имя хоста из SSH config (например, "asgef_fvds_db-tunnel")
        remote_bind_address: Адрес и порт на удалённом сервере (host, port)
        local_bind_address: Адрес и порт для локального проброса (host, port)
    
    Yields:
        SSHTunnelForwarder: Объект туннеля
    
    Example:
        ```python
        with ssh_tunnel_from_config(ssh_config_host="asgef_fvds_db-tunnel"):
            # Подключение к БД через localhost:5433
            pass
        ```
    """
    if ssh_config_host is None:
        # Пробуем получить из переменной окружения
        ssh_config_host = os.getenv("SSH_TUNNEL_HOST", "asgef_fvds_db-tunnel")
    
    # Парсим SSH config для получения параметров
    from pathlib import Path
    
    ssh_config_path = Path.home() / ".ssh" / "config"
    
    if not ssh_config_path.exists():
        raise FileNotFoundError(f"SSH config не найден: {ssh_config_path}")
    
    # Читаем SSH config (это не стандартный INI, но попробуем)
    # Для более надёжного парсинга можно использовать paramiko.config
    try:
        from paramiko.config import SSHConfig
        
        with open(ssh_config_path) as f:
            config = SSHConfig()
            config.parse(f)
            host_config = config.lookup(ssh_config_host)
    except Exception as e:
        logger.warning(f"Не удалось распарсить SSH config: {e}")
        logger.warning("Используем значения по умолчанию")
        host_config = {}
    
    ssh_host = host_config.get("hostname", "188.120.247.71")
    ssh_port = int(host_config.get("port", 22))
    ssh_username = host_config.get("user", "devuser_1")
    
    # Получаем путь к ключу
    identity_file = host_config.get("identityfile")
    if identity_file:
        ssh_private_key = os.path.expanduser(identity_file[0])
    else:
        ssh_private_key = None
    
    # Используем remote_bind_address из LocalForward, если есть
    local_forward = host_config.get("localforward")
    if local_forward:
        # localforward может быть строкой или списком строк
        if isinstance(local_forward, list):
            # Берём первый элемент списка
            local_forward_str = local_forward[0] if local_forward else ""
        else:
            local_forward_str = str(local_forward)
        
        # Формат: "5433 localhost:5433"
        parts = local_forward_str.split()
        if len(parts) >= 2:
            local_port = int(parts[0])
            remote_part = parts[1]
            if ":" in remote_part:
                remote_host, remote_port = remote_part.split(":")
                remote_bind_address = (remote_host, int(remote_port))
                local_bind_address = ("127.0.0.1", local_port)
    
    with ssh_tunnel(
        ssh_host=ssh_host,
        ssh_port=ssh_port,
        ssh_username=ssh_username,
        ssh_private_key=ssh_private_key,
        remote_bind_address=remote_bind_address,
        local_bind_address=local_bind_address,
    ):
        yield
