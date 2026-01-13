import logging
from typing import Optional, List, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.application.repositories import IUserRepository
from src.domain.models import User

logger = logging.getLogger(__name__)


class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: Any) -> Optional[User]:
        try:
            stmt = select(User).where(User.id == item_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                logger.debug(f"Retrieved user {item_id}.")
            else:
                logger.debug(f"User {item_id} not found.")
            return user
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_by_id for user {item_id}: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_by_id for user {item_id}: {e}", exc_info=True
            )
            raise

    async def add(self, user: User) -> User:
        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            logger.info(f"Added new user {user.id}.")
            return user
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError in add user {user.id}: {e}", exc_info=True)
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error in add user {user.id}: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def update(self, user: User) -> User:
        try:
            await self.session.commit()
            await self.session.refresh(user)
            logger.info(f"Updated user {user.id}.")
            return user
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in update user {user.id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in update user {user.id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise

    async def delete(self, item_id: Any) -> None:
        try:
            user = await self.get_by_id(item_id)
            if user:
                await self.session.delete(user)
                await self.session.commit()
                logger.info(f"Deleted user {item_id}.")
            else:
                logger.warning(f"Attempted to delete non-existent user {item_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in delete user {item_id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in delete user {item_id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        try:
            stmt = select(User).where(User.id == telegram_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                logger.debug(f"Retrieved user by Telegram ID {telegram_id}.")
            else:
                logger.debug(f"User by Telegram ID {telegram_id} not found.")
            return user
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_by_telegram_id for Telegram ID {telegram_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_by_telegram_id for Telegram ID {telegram_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_admin_approved_users(self) -> List[User]:
        try:
            stmt = select(User).where(User.is_registered.is_(True))
            result = await self.session.execute(stmt)
            users = list(result.scalars().all())
            logger.debug(f"Retrieved {len(users)} admin approved users.")
            return users
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_admin_approved_users: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_admin_approved_users: {e}", exc_info=True
            )
            raise

    async def save_google_sheet_config(
        self, user_id: int, url: str, spreadsheet_id: str
    ) -> None:
        try:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(google_sheet_url=url, spreadsheet_id=spreadsheet_id)
            )
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info(f"Saved Google Sheet config for user {user_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in save_google_sheet_config for user {user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in save_google_sheet_config for user {user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
