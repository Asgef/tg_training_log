import logging
from src.application.repositories import IUserRepository
from src.application.use_cases import IRegistrationUseCase
from src.domain.models import User

logger = logging.getLogger(__name__)


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
                    f"Запрос на регистрацию для существующего пользователя {telegram_id}. Пропуск."
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
            logger.info(f"Пользователь {telegram_id} успешно отправил запрос на регистрацию.")
            return True
        except Exception as e:
            logger.error(f"Ошибка при запросе регистрации для пользователя {telegram_id}: {e}")
            return False

    async def approve_registration(self, user_id: int) -> bool:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if user and not user.is_registered:
                user.is_registered = True
                await self.user_repository.update(user)
                logger.info(f"Регистрация пользователя {user_id} одобрена.")
                return True
            logger.warning(
                f"Не удалось одобрить регистрацию для пользователя {user_id}: Пользователь не найден или уже зарегистрирован."
            )
            return False
        except Exception as e:
            logger.error(f"Ошибка при одобрении регистрации для пользователя {user_id}: {e}")
            return False

    async def reject_registration(self, user_id: int) -> bool:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if user and not user.is_registered:
                await self.user_repository.delete(user_id)
                logger.info(f"Регистрация пользователя {user_id} отклонена и запись удалена.")
                return True
            logger.warning(
                f"Не удалось отклонить регистрацию для пользователя {user_id}: Пользователь не найден или уже зарегистрирован."
            )
            return False
        except Exception as e:
            logger.error(f"Ошибка при отклонении регистрации для пользователя {user_id}: {e}")
            return False
