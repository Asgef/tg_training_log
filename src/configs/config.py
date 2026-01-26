import os
import json
import logging
from pathlib import Path
from typing import List, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()


class Config:
    """Конфигурация приложения, загружаемая из переменных окружения."""

    def __init__(self):
        # Telegram Bot
        self.bot_token: str = os.getenv("BOT_TOKEN", "")
        if not self.bot_token:
            logger.warning("BOT_TOKEN не установлен в переменных окружения")

        # Database
        self.database_url: str = os.getenv("DATABASE_URL", "")
        if not self.database_url:
            logger.error(
                "Переменная окружения DATABASE_URL не установлена. Подключение к базе данных не удастся."
            )

        # Admin IDs
        admin_id_str = os.getenv("ADMIN_ID", "")
        self.admin_ids: List[int] = [
            int(admin_id.strip())
            for admin_id in admin_id_str.split(",")
            if admin_id.strip()
        ]
        if not self.admin_ids:
            logger.warning("ADMIN_ID не установлен в переменных окружения")

        # Google Sheets
        self.google_credentials_json: str = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
        if not self.google_credentials_json:
            logger.warning(
                "GOOGLE_CREDENTIALS_JSON не установлен в переменных окружения"
            )
        
        # Google Sheets Service Account Email
        self.service_account_email: str = os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_EMAIL",
            "tg-training@tgtraining.iam.gserviceaccount.com"
        )

        # Rollbar
        self.rollbar_token: str = os.getenv("ROLLBAR", "")
        if not self.rollbar_token:
            logger.warning("ROLLBAR токен не установлен в переменных окружения")
        
        # Environment для Rollbar (production, development, staging и т.д.)
        self.rollbar_environment: str = os.getenv("ENVIRONMENT", "production")
        
        # Code version для Rollbar (опционально, можно использовать git commit hash)
        self.rollbar_code_version: str = os.getenv("CODE_VERSION", "")

        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", "DEBUG").upper()
        # Умный fallback для пути к логам: если путь начинается с /app и директории нет - используем локальный путь
        log_file_path_env = os.getenv("LOG_FILE_PATH")
        
        # Определяем корень проекта (директория с .env файлом)
        # dotenv ищет .env начиная с текущей директории и выше
        project_root = Path.cwd()
        env_file = Path(".env")
        if not env_file.exists():
            # Пытаемся найти .env в родительских директориях
            current = Path.cwd()
            for _ in range(5):  # Максимум 5 уровней вверх
                if (current / ".env").exists():
                    project_root = current
                    break
                parent = current.parent
                if parent == current:  # Достигли корня ФС
                    break
                current = parent
        
        if log_file_path_env:
            log_path = Path(log_file_path_env)
            # Если путь абсолютный и начинается с /app, проверяем существование
            if log_path.is_absolute() and str(log_path).startswith("/app"):
                if not Path("/app").exists():
                    # Локальное окружение: используем абсолютный путь относительно корня проекта
                    self.log_file_path = str((project_root / "logs" / "app.log").resolve())
                    logger.info(
                        f"Директория /app не найдена (локальное окружение), "
                        f"используется fallback путь: {self.log_file_path}"
                    )
                else:
                    # Docker окружение: используем как есть
                    self.log_file_path = log_file_path_env
            elif not log_path.is_absolute():
                # Относительный путь - разрешаем относительно корня проекта
                self.log_file_path = str((project_root / log_path).resolve())
            else:
                # Абсолютный путь (не /app) - используем как есть
                self.log_file_path = log_file_path_env
        else:
            # Если не задан - используем абсолютный путь относительно корня проекта
            self.log_file_path = str((project_root / "logs" / "app.log").resolve())
        
        self.log_rotate_when: str = os.getenv("LOG_ROTATE_WHEN", "midnight")
        self.log_rotate_interval: int = int(os.getenv("LOG_ROTATE_INTERVAL", "1"))
        self.log_rotate_backup_count: int = int(os.getenv("LOG_ROTATE_BACKUP_COUNT", "7"))

    def get_google_credentials_dict(self) -> dict[str, Any]:
        """Возвращает Google credentials в виде словаря."""
        if not self.google_credentials_json:
            raise ValueError(
                "Переменная окружения GOOGLE_CREDENTIALS_JSON не установлена."
            )
        try:
            return json.loads(self.google_credentials_json)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Не удалось распарсить GOOGLE_CREDENTIALS_JSON: {e}"
            ) from e


# Глобальный экземпляр конфигурации
config = Config()
