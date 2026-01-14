"""DTO для тренировочных сессий."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WorkoutSessionDTO(BaseModel):
    """Data Transfer Object для тренировочной сессии."""

    id: int = Field(..., description="ID сессии")
    user_id: int = Field(..., description="ID пользователя")
    started_at: datetime = Field(..., description="Время начала тренировки")
    ended_at: Optional[datetime] = Field(None, description="Время окончания тренировки")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    @property
    def is_active(self) -> bool:
        """Проверка, активна ли тренировка."""
        return self.ended_at is None

    class Config:
        """Конфигурация Pydantic."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
