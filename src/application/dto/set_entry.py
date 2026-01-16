"""DTO для записей подходов."""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class SetEntryDTO(BaseModel):
    """Data Transfer Object для записи подхода."""

    id: int = Field(..., description="ID записи")
    session_id: int = Field(..., description="ID тренировочной сессии")
    machine_id: int = Field(..., description="ID тренажёра")
    weight: float = Field(..., description="Вес в килограммах")
    reps: int = Field(..., description="Количество повторений")
    is_failure: bool = Field(default=False, description="Был ли отказ")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

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

    class Config:
        """Конфигурация Pydantic."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
