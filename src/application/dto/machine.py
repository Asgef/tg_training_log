"""DTO для тренажёров и мышц."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class MuscleGroupDTO(BaseModel):
    """Data Transfer Object для группы мышц."""

    id: int = Field(..., description="ID группы мышц")
    name: str = Field(..., description="Название группы мышц")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Валидация названия группы мышц."""
        if not v or not v.strip():
            raise ValueError("Название группы мышц не может быть пустым")
        return v.strip()

    class Config:
        """Конфигурация Pydantic."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class MuscleDTO(BaseModel):
    """Data Transfer Object для мышцы."""

    id: int = Field(..., description="ID мышцы")
    name: str = Field(..., description="Название мышцы")
    group_id: int = Field(..., description="ID группы мышц")
    group: Optional[MuscleGroupDTO] = Field(None, description="Группа мышц")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Валидация названия мышцы."""
        if not v or not v.strip():
            raise ValueError("Название мышцы не может быть пустым")
        return v.strip()

    class Config:
        """Конфигурация Pydantic."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class MachineDTO(BaseModel):
    """Data Transfer Object для тренажёра."""

    id: int = Field(..., description="ID тренажёра")
    user_id: int = Field(..., description="ID пользователя")
    name: str = Field(..., description="Название тренажёра")
    photo_file_id: Optional[str] = Field(None, description="Telegram file_id фото")
    is_archived: bool = Field(default=False, description="Статус архивации")
    muscles: List[MuscleDTO] = Field(default_factory=list, description="Список мышц")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Валидация названия тренажёра."""
        if not v or not v.strip():
            raise ValueError("Название тренажёра не может быть пустым")
        return v.strip()

    class Config:
        """Конфигурация Pydantic."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
