import os
import json
import logging
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
