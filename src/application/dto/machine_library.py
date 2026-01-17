"""DTO для библиотечных тренажёров."""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator

from .machine import MuscleDTO, MuscleZoneDTO


class MachineLibraryItemDTO(BaseModel):
    """DTO для списка библиотечных тренажёров."""

    id: int = Field(..., description="ID библиотечного тренажёра")
    name_ru: str = Field(..., description="Каноническое название (RU)")
    aliases: List[str] = Field(default_factory=list, description="Алиасы")

    @field_validator("name_ru")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Название тренажёра не может быть пустым")
        return v.strip()

    class Config:
        from_attributes = True


class MachineLibraryDTO(BaseModel):
    """DTO для карточки библиотечного тренажёра."""

    id: int = Field(..., description="ID библиотечного тренажёра")
    name_ru: str = Field(..., description="Каноническое название (RU)")
    aliases: List[str] = Field(default_factory=list, description="Алиасы")
    zones: List[MuscleZoneDTO] = Field(default_factory=list, description="Зоны")
    muscles: List[MuscleDTO] = Field(default_factory=list, description="Мышцы")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    @field_validator("name_ru")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Название тренажёра не может быть пустым")
        return v.strip()

    class Config:
        from_attributes = True
