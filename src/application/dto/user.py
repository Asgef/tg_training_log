"""DTO для пользователя."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UserDTO(BaseModel):
    """Data Transfer Object для пользователя."""

    id: int = Field(..., description="ID пользователя")
    telegram_id: Optional[int] = Field(None, description="Telegram ID пользователя")
    is_registered: bool = Field(default=False, description="Статус регистрации")
    google_sheet_url: Optional[str] = Field(None, description="URL Google таблицы")
    spreadsheet_id: Optional[str] = Field(None, description="ID Google таблицы")
    telegram_username: Optional[str] = Field(None, description="Telegram username")
    telegram_firstname: Optional[str] = Field(None, description="Telegram имя")
    telegram_lastname: Optional[str] = Field(None, description="Telegram фамилия")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    timezone: str = Field(default="Europe/Moscow", description="Временная зона")

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Валидация временной зоны."""
        if not v or not v.strip():
            return "Europe/Moscow"
        return v.strip()

    class Config:
        """Конфигурация Pydantic."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
