import structlog
from typing import Optional
from src.application.repositories import IUserRepository
from src.application.use_case_interfaces import IRegistrationUseCase
from src.domain.models import User

logger = structlog.get_logger(__name__)


class RegistrationUseCase(IRegistrationUseCase):
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    async def request_registration(
        self,
        telegram_id: int,
        username: str,
        first_name: str,
        last_name: str,
        description: str,
    ) -> bool:
        try:
            existing_user = await self.user_repository.get_by_telegram_id(telegram_id)
            if existing_user:
                logger.info(
                    "Запрос на регистрацию для существующего пользователя. Пропуск.",
                    telegram_id=telegram_id,
                )
                return False

            new_user = User(
                id=telegram_id,
                telegram_username=username,
                telegram_firstname=first_name,
                telegram_lastname=last_name,
                is_registered=False,
            )
            await self.user_repository.add(new_user)
            logger.info("Пользователь успешно отправил запрос на регистрацию.", telegram_id=telegram_id)
            return True
        except Exception as e:
            logger.error("Ошибка при запросе регистрации", telegram_id=telegram_id, error=str(e), exc_info=True)
            return False

    async def approve_registration(self, user_id: int) -> bool:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if user and not user.is_registered:
                user.is_registered = True
                await self.user_repository.update(user)
                logger.info("Регистрация пользователя одобрена.", user_id=user_id)
                return True
            logger.warning(
                "Не удалось одобрить регистрацию: Пользователь не найден или уже зарегистрирован.",
                user_id=user_id,
            )
            return False
        except Exception as e:
            logger.error("Ошибка при одобрении регистрации", user_id=user_id, error=str(e), exc_info=True)
            return False

    async def reject_registration(self, user_id: int) -> bool:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if user and not user.is_registered:
                await self.user_repository.delete(user_id)
                logger.info("Регистрация пользователя отклонена и запись удалена.", user_id=user_id)
                return True
            logger.warning(
                "Не удалось отклонить регистрацию: Пользователь не найден или уже зарегистрирован.",
                user_id=user_id,
            )
            return False
        except Exception as e:
            logger.error("Ошибка при отклонении регистрации", user_id=user_id, error=str(e), exc_info=True)
            return False

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получает пользователя по Telegram ID."""
        try:
            user = await self.user_repository.get_by_telegram_id(telegram_id)
            return user
        except Exception as e:
            logger.error("Ошибка при получении пользователя", telegram_id=telegram_id, error=str(e), exc_info=True)
            return None

    async def check_user_registered(self, telegram_id: int) -> bool:
        """Проверяет, зарегистрирован ли пользователь."""
        try:
            user = await self.user_repository.get_by_telegram_id(telegram_id)
            return user is not None and user.is_registered
        except Exception as e:
            logger.error("Ошибка при проверке регистрации пользователя", telegram_id=telegram_id, error=str(e), exc_info=True)
            return False
