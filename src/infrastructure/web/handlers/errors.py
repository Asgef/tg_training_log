"""Кастомные исключения и стандартизированные сообщения об ошибках."""
from typing import Optional


class BaseApplicationError(Exception):
    """Базовый класс для всех ошибок приложения.
    
    Все кастомные исключения должны наследоваться от этого класса.
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        """
        Args:
            message: Техническое сообщение для логирования
            user_message: Понятное сообщение для пользователя
            error_code: Код ошибки для классификации
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.error_code = error_code


class ValidationError(BaseApplicationError):
    """Ошибка валидации данных.
    
    Используется когда входные данные не соответствуют ожидаемому формату.
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        field: Optional[str] = None,
    ):
        """
        Args:
            message: Техническое сообщение
            user_message: Сообщение для пользователя
            field: Поле, которое не прошло валидацию
        """
        super().__init__(
            message=message,
            user_message=user_message or f"Ошибка валидации: {message}",
            error_code="VALIDATION_ERROR",
        )
        self.field = field


class MachineNotFoundError(BaseApplicationError):
    """Ошибка когда тренажёр не найден."""
    
    def __init__(
        self,
        machine_id: Optional[int] = None,
        machine_name: Optional[str] = None,
        user_message: Optional[str] = None,
    ):
        """
        Args:
            machine_id: ID тренажёра, который не найден
            machine_name: Название тренажёра, который не найден
            user_message: Кастомное сообщение для пользователя
        """
        if machine_id:
            message = f"Machine with id {machine_id} not found"
            default_user_message = f"Тренажёр с ID {machine_id} не найден."
        elif machine_name:
            message = f"Machine with name '{machine_name}' not found"
            default_user_message = f"Тренажёр '{machine_name}' не найден."
        else:
            message = "Machine not found"
            default_user_message = "Тренажёр не найден."
        
        super().__init__(
            message=message,
            user_message=user_message or default_user_message,
            error_code="MACHINE_NOT_FOUND",
        )
        self.machine_id = machine_id
        self.machine_name = machine_name


class WorkoutNotActiveError(BaseApplicationError):
    """Ошибка когда у пользователя нет активной тренировки."""
    
    def __init__(self, user_message: Optional[str] = None):
        """
        Args:
            user_message: Кастомное сообщение для пользователя
        """
        super().__init__(
            message="No active workout session found",
            user_message=user_message or "У вас нет активной тренировки. Начните тренировку командой /workout_start",
            error_code="WORKOUT_NOT_ACTIVE",
        )


class WorkoutAlreadyActiveError(BaseApplicationError):
    """Ошибка когда у пользователя уже есть активная тренировка."""
    
    def __init__(self, user_message: Optional[str] = None):
        """
        Args:
            user_message: Кастомное сообщение для пользователя
        """
        super().__init__(
            message="User already has an active workout session",
            user_message=user_message or "У вас уже есть активная тренировка. Завершите её, прежде чем начинать новую.",
            error_code="WORKOUT_ALREADY_ACTIVE",
        )


class ExternalAPIError(BaseApplicationError):
    """Ошибка при взаимодействии с внешним API (например, Google Sheets)."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        api_name: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        """
        Args:
            message: Техническое сообщение
            user_message: Сообщение для пользователя
            api_name: Название API (например, "Google Sheets")
            status_code: HTTP статус код (если применимо)
        """
        super().__init__(
            message=message,
            user_message=user_message or f"Ошибка при взаимодействии с {api_name or 'внешним сервисом'}. Попробуйте позже.",
            error_code="EXTERNAL_API_ERROR",
        )
        self.api_name = api_name
        self.status_code = status_code


class UserNotFoundError(BaseApplicationError):
    """Ошибка когда пользователь не найден."""
    
    def __init__(
        self,
        telegram_id: Optional[int] = None,
        user_message: Optional[str] = None,
    ):
        """
        Args:
            telegram_id: Telegram ID пользователя
            user_message: Кастомное сообщение для пользователя
        """
        if telegram_id:
            message = f"User with telegram_id {telegram_id} not found"
        else:
            message = "User not found"
        
        super().__init__(
            message=message,
            user_message=user_message or "Пользователь не найден.",
            error_code="USER_NOT_FOUND",
        )
        self.telegram_id = telegram_id


class PermissionDeniedError(BaseApplicationError):
    """Ошибка когда у пользователя нет прав для выполнения действия."""
    
    def __init__(self, user_message: Optional[str] = None):
        """
        Args:
            user_message: Кастомное сообщение для пользователя
        """
        super().__init__(
            message="Permission denied",
            user_message=user_message or "У вас нет прав для выполнения этой операции.",
            error_code="PERMISSION_DENIED",
        )


class DatabaseError(BaseApplicationError):
    """Ошибка при работе с базой данных."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
    ):
        """
        Args:
            message: Техническое сообщение
            user_message: Сообщение для пользователя
        """
        super().__init__(
            message=message,
            user_message=user_message or "Произошла ошибка при работе с базой данных. Попробуйте позже.",
            error_code="DATABASE_ERROR",
        )


# Стандартизированные сообщения об ошибках
class ErrorMessages:
    """Стандартизированные сообщения об ошибках для пользователей."""
    
    # Общие ошибки
    GENERIC_ERROR = "Произошла непредвиденная ошибка. Попробуйте позже или обратитесь к администратору."
    VALIDATION_ERROR = "Ошибка валидации данных. Проверьте введённые данные и попробуйте ещё раз."
    PERMISSION_DENIED = "У вас нет прав для выполнения этой операции."
    
    # Ошибки тренировок
    WORKOUT_NOT_ACTIVE = "У вас нет активной тренировки. Начните тренировку командой /workout_start"
    WORKOUT_ALREADY_ACTIVE = "У вас уже есть активная тренировка. Завершите её, прежде чем начинать новую."
    
    # Ошибки тренажёров
    MACHINE_NOT_FOUND = "Тренажёр не найден."
    MACHINE_ALREADY_EXISTS = "Тренажёр с таким названием уже существует."
    
    # Ошибки пользователей
    USER_NOT_FOUND = "Пользователь не найден."
    USER_NOT_REGISTERED = "Для использования бота вам необходимо зарегистрироваться."
    
    # Ошибки внешних API
    EXTERNAL_API_ERROR = "Ошибка при взаимодействии с внешним сервисом. Попробуйте позже."
    GOOGLE_SHEETS_ERROR = "Ошибка при работе с Google Sheets. Проверьте настройки и попробуйте позже."
    
    # Ошибки базы данных
    DATABASE_ERROR = "Произошла ошибка при работе с базой данных. Попробуйте позже."
