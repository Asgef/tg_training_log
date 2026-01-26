"""Настройка структурированного логирования с использованием structlog."""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Optional

import structlog
from structlog.types import EventDict


def mask_pii_processor(logger: Any, name: str, event_dict: EventDict) -> EventDict:
    """Процессор для маскирования PII данных в логах.
    
    Маскирует:
    - user_id (оставляет последние 4 цифры)
    - chat_id (оставляет последние 4 цифры)
    - email адреса
    - токены и секреты
    """
    def mask_value(value: Any) -> Any:
        """Маскирует значение если оно содержит PII."""
        if isinstance(value, str):
            # Маскируем email адреса
            if "@" in value and "." in value:
                parts = value.split("@")
                if len(parts) == 2:
                    username = parts[0]
                    domain = parts[1]
                    if len(username) > 2:
                        masked_username = username[:2] + "*" * (len(username) - 2)
                    else:
                        masked_username = "*" * len(username)
                    return f"{masked_username}@{domain}"
            
            # Маскируем токены (длинные строки > 20 символов)
            if len(value) > 20 and any(keyword in value.lower() for keyword in ["token", "secret", "key", "password"]):
                return value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
        
        return value
    
    # Маскируем user_id и chat_id (оставляем последние 4 цифры)
    for key in ["user_id", "chat_id", "from_user_id", "telegram_user_id"]:
        if key in event_dict:
            value = event_dict[key]
            if isinstance(value, (int, str)):
                value_str = str(value)
                if len(value_str) > 4:
                    event_dict[key] = "*" * (len(value_str) - 4) + value_str[-4:]
                else:
                    event_dict[key] = "*" * len(value_str)
    
    # Маскируем все строковые значения в event_dict
    for key, value in event_dict.items():
        if key not in ["user_id", "chat_id", "from_user_id", "telegram_user_id", "correlation_id", "update_id"]:
            event_dict[key] = mask_value(value)
    
    return event_dict


def setup_logging(
    log_level: str = "DEBUG",
    log_file_path: Optional[str] = None,
    log_rotate_when: str = "midnight",
    log_rotate_interval: int = 1,
    log_rotate_backup_count: int = 7,
) -> None:
    """Настраивает структурированное логирование с JSON форматом.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file_path: Путь к файлу логов (опционально)
        log_rotate_when: Когда ротировать логи ('S', 'M', 'H', 'D', 'midnight')
        log_rotate_interval: Интервал ротации
        log_rotate_backup_count: Количество файлов для хранения
    """
    log_level_name = log_level.upper()
    log_level_value = logging._nameToLevel.get(log_level_name, logging.DEBUG)

    # Создаём список handlers: всегда stdout для Docker logs
    handlers = [
        logging.StreamHandler(sys.stdout),
    ]
    
    # Добавляем TimedRotatingFileHandler если указан путь к файлу
    if log_file_path:
        try:
            log_dir = Path(log_file_path).parent
            if log_dir:
                # Создаём директорию если её нет
                log_dir.mkdir(parents=True, exist_ok=True)
            
            # TimedRotatingFileHandler с UTF-8 для корректной записи кириллицы
            # Ротация по времени с настраиваемыми параметрами
            file_handler = TimedRotatingFileHandler(
                log_file_path,
                when=log_rotate_when,
                interval=log_rotate_interval,
                backupCount=log_rotate_backup_count,
                encoding='utf-8'
            )
            handlers.append(file_handler)
        except (PermissionError, OSError) as e:
            # Если не удалось создать директорию или файл - используем только stdout
            # Это нормально для некоторых окружений (например, read-only FS)
            print(
                f"WARNING: Не удалось создать файловый handler для логов: {e}. "
                f"Используется только stdout.",
                file=sys.stderr
            )

    # Настраиваем стандартный logging для совместимости (stdout + файл при необходимости)
    logging.basicConfig(
        format="%(message)s",
        level=log_level_value,
        handlers=handlers,
        force=True,
    )
    
    # Отключаем детальные логи httpcore/httpx (они слишком шумные)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
    logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
    
    # Настраиваем логирование Rollbar (убираем детальные payload логи)
    logging.getLogger("rollbar").setLevel(logging.WARNING)
    
    # Настраиваем structlog
    structlog.configure(
        processors=[
            # Добавляем контекстные переменные
            structlog.contextvars.merge_contextvars,
            # Добавляем информацию о времени
            structlog.processors.TimeStamper(fmt="iso"),
            # Добавляем уровень логирования
            structlog.processors.add_log_level,
            # Добавляем информацию о месте вызова (включая имя модуля)
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            ),
            # Маскируем PII данные
            mask_pii_processor,
            # Форматируем исключения
            structlog.processors.format_exc_info,
            # Преобразуем в JSON (ensure_ascii=False для корректного отображения кириллицы)
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level_value),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
