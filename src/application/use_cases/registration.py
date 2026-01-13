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
                    f"Registration request for existing user {telegram_id}. Skipping."
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
            logger.info(f"User {telegram_id} requested registration successfully.")
            return True
        except Exception as e:
            logger.error(f"Error requesting registration for user {telegram_id}: {e}")
            return False

    async def approve_registration(self, user_id: int) -> bool:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if user and not user.is_registered:
                user.is_registered = True
                await self.user_repository.update(user)
                logger.info(f"User {user_id} registration approved.")
                return True
            logger.warning(
                f"Failed to approve registration for user {user_id}: User not found or already registered."
            )
            return False
        except Exception as e:
            logger.error(f"Error approving registration for user {user_id}: {e}")
            return False

    async def reject_registration(self, user_id: int) -> bool:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if user and not user.is_registered:
                await self.user_repository.delete(user_id)
                logger.info(f"User {user_id} registration rejected and entry deleted.")
                return True
            logger.warning(
                f"Failed to reject registration for user {user_id}: User not found or already registered."
            )
            return False
        except Exception as e:
            logger.error(f"Error rejecting registration for user {user_id}: {e}")
            return False
