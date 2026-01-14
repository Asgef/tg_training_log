"""Настройка структурированного логирования с использованием structlog."""
import logging
import sys
from typing import Any

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


def setup_logging() -> None:
    """Настраивает структурированное логирование с JSON форматом."""
    # Настраиваем стандартный logging для совместимости
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Настраиваем structlog
    structlog.configure(
        processors=[
            # Добавляем контекстные переменные
            structlog.contextvars.merge_contextvars,
            # Добавляем информацию о времени
            structlog.processors.TimeStamper(fmt="iso"),
            # Добавляем уровень логирования
            structlog.processors.add_log_level,
            # Добавляем имя логгера
            structlog.processors.add_logger_name,
            # Маскируем PII данные
            mask_pii_processor,
            # Форматируем исключения
            structlog.processors.format_exc_info,
            # Преобразуем в JSON
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
