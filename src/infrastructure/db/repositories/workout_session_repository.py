import logging
from typing import Optional, Any
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.application.repositories import IWorkoutSessionRepository
from src.domain.models import WorkoutSession

logger = logging.getLogger(__name__)


class WorkoutSessionRepository(IWorkoutSessionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: Any) -> Optional[WorkoutSession]:
        try:
            stmt = select(WorkoutSession).where(WorkoutSession.id == item_id)
            result = await self.session.execute(stmt)
            session = result.scalar_one_or_none()
            if session:
                logger.debug(f"Получена тренировка {item_id}.")
            else:
                logger.debug(f"Тренировка {item_id} не найдена.")
            return session
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_by_id для тренировки {item_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_by_id для тренировки {item_id}: {e}",
                exc_info=True,
            )
            raise

    async def add(self, session: WorkoutSession) -> WorkoutSession:
        try:
            self.session.add(session)
            await self.session.commit()
            await self.session.refresh(session)
            logger.info(
                f"Добавлена новая тренировка {session.id} для пользователя {session.user_id}."
            )
            return session
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при добавлении тренировки для пользователя {session.user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при добавлении тренировки для пользователя {session.user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def update(self, session: WorkoutSession) -> WorkoutSession:
        try:
            await self.session.commit()
            await self.session.refresh(session)
            logger.info(f"Обновлена тренировка {session.id}.")
            return session
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при обновлении тренировки {session.id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при обновлении тренировки {session.id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def delete(self, item_id: Any) -> None:
        try:
            session = await self.get_by_id(item_id)
            if session:
                await self.session.delete(session)
                await self.session.commit()
                logger.info(f"Удалена тренировка {item_id}.")
            else:
                logger.warning(
                    f"Попытка удалить несуществующую тренировку {item_id}."
                )
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError при удалении тренировки {item_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при удалении тренировки {item_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def get_active_session_for_user(
        self, user_id: int
    ) -> Optional[WorkoutSession]:
        try:
            stmt = select(WorkoutSession).where(
                WorkoutSession.user_id == user_id, WorkoutSession.ended_at.is_(None)
            )
            result = await self.session.execute(stmt)
            session = result.scalar_one_or_none()
            if session:
                logger.debug(
                    f"Retrieved active session {session.id} for user {user_id}."
                )
            else:
                logger.debug(f"Активная сессия для пользователя {user_id} не найдена.")
            return session
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в get_active_session_for_user для пользователя {user_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в get_active_session_for_user для пользователя {user_id}: {e}",
                exc_info=True,
            )
            raise

    async def start_session(self, user_id: int) -> WorkoutSession:
        try:
            new_session = WorkoutSession(user_id=user_id, started_at=datetime.utcnow())
            self.session.add(new_session)
            await self.session.commit()
            await self.session.refresh(new_session)
            logger.info(
                f"Started new workout session {new_session.id} for user {user_id}."
            )
            return new_session
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в start_session для пользователя {user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в start_session для пользователя {user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def end_session(self, session_id: int) -> None:
        try:
            stmt = (
                update(WorkoutSession)
                .where(WorkoutSession.id == session_id)
                .values(ended_at=datetime.utcnow())
            )
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info(f"Ended workout session {session_id}.")
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError в end_session для тренировки {session_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка в end_session для тренировки {session_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
