"""DTO для валидации входных данных от пользователей.

Все сообщения об ошибках стандартизированы для единообразия.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SetEntryInputDTO(BaseModel):
    """DTO для валидации данных подхода от пользователя."""

    machine_id: int = Field(..., gt=0, description="ID тренажёра")
    weight: float = Field(..., gt=0, description="Вес в килограммах")
    reps: int = Field(..., gt=0, description="Количество повторений")
    failure: bool = Field(default=False, description="Был ли отказ")

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        """Валидация веса."""
        if v <= 0:
            raise ValueError("Вес должен быть больше 0")
        return v

    @field_validator("reps")
    @classmethod
    def validate_reps(cls, v: int) -> int:
        """Валидация количества повторений."""
        if v <= 0:
            raise ValueError("Количество повторений должно быть больше 0")
        return v


class MachineInputDTO(BaseModel):
    """DTO для валидации данных тренажёра от пользователя."""

    name: str = Field(..., min_length=1, description="Название тренажёра")
    photo_file_id: Optional[str] = Field(None, description="Telegram file_id фото")
    zone_ids: list[int] = Field(default_factory=list, description="Список ID зон")
    muscle_ids: list[int] = Field(default_factory=list, description="Список ID мышц")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Валидация названия тренажёра."""
        if not v or not v.strip():
            raise ValueError("Название тренажёра не может быть пустым")
        return v.strip()


class MachineUpdateInputDTO(BaseModel):
    """DTO для валидации данных обновления тренажёра."""

    name: Optional[str] = Field(None, min_length=1, description="Название тренажёра")
    photo_file_id: Optional[str] = Field(None, description="Telegram file_id фото")
    zone_ids: Optional[list[int]] = Field(None, description="Список ID зон")
    muscle_ids: Optional[list[int]] = Field(None, description="Список ID мышц")
    is_archived: Optional[bool] = Field(None, description="Статус архивации")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Валидация названия тренажёра."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Название тренажёра не может быть пустым")
            return v.strip()
        return v


class RegistrationInputDTO(BaseModel):
    """DTO для валидации данных регистрации."""

    telegram_id: int = Field(..., gt=0, description="Telegram ID пользователя")
    username: str = Field(default="", description="Telegram username")
    first_name: str = Field(default="", description="Telegram имя")
    last_name: str = Field(default="", description="Telegram фамилия")
    description: str = Field(..., min_length=1, description="Описание пользователя")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Валидация описания."""
        if not v or not v.strip():
            raise ValueError("Описание не может быть пустым")
        return v.strip()


class GoogleSheetsConfigInputDTO(BaseModel):
    """DTO для валидации конфигурации Google Sheets."""

    sheet_url: str = Field(..., min_length=1, description="URL Google таблицы")

    @field_validator("sheet_url")
    @classmethod
    def validate_sheet_url(cls, v: str) -> str:
        """Валидация URL таблицы."""
        if not v or not v.strip():
            raise ValueError("URL таблицы не может быть пустым")
        if not v.startswith(("https://docs.google.com/spreadsheets/", "https://docs.google.com/spreadsheets/d/")):
            raise ValueError("URL должен быть ссылкой на Google Spreadsheet")
        return v.strip()
