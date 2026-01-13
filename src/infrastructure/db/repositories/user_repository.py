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
                logger.debug(f"Получен пользователь {item_id}.")
            else:
                logger.debug(f"Пользователь {item_id} не найден.")
            return user
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_by_id для пользователя {item_id}: {e}", exc_info=True
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
            logger.info(f"Добавлен новый пользователь {user.id}.")
            return user
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError in add user {user.id}: {e}", exc_info=True)
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при добавлении пользователя {user.id}: {e}", exc_info=True)
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
                f"SQLAlchemyError при обновлении пользователя {user.id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при обновлении пользователя {user.id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise

    async def delete(self, item_id: Any) -> None:
        try:
            user = await self.get_by_id(item_id)
            if user:
                await self.session.delete(user)
                await self.session.commit()
                logger.info(f"Удалён пользователь {item_id}.")
            else:
                logger.warning(f"Попытка удалить несуществующего пользователя {item_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при удалении пользователя {item_id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при удалении пользователя {item_id}: {e}", exc_info=True
            )
            await self.session.rollback()
            raise

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        try:
            stmt = select(User).where(User.id == telegram_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                logger.debug(f"Получен пользователь по Telegram ID {telegram_id}.")
            else:
                logger.debug(f"Пользователь по Telegram ID {telegram_id} не найден.")
            return user
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_by_telegram_id для Telegram ID {telegram_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_by_telegram_id для Telegram ID {telegram_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_admin_approved_users(self) -> List[User]:
        try:
            stmt = select(User).where(User.is_registered.is_(True))
            result = await self.session.execute(stmt)
            users = list(result.scalars().all())
            logger.debug(f"Получено {len(users)} одобренных администратором пользователей.")
            return users
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_admin_approved_users: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_admin_approved_users: {e}", exc_info=True
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
            logger.info(f"Сохранена конфигурация Google Sheet для пользователя {user_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в save_google_sheet_config для пользователя {user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в save_google_sheet_config для пользователя {user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
