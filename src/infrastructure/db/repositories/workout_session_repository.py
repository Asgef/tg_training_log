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
                logger.debug(f"Retrieved workout session {item_id}.")
            else:
                logger.debug(f"Workout session {item_id} not found.")
            return session
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_by_id for session {item_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_by_id for session {item_id}: {e}",
                exc_info=True,
            )
            raise

    async def add(self, session: WorkoutSession) -> WorkoutSession:
        try:
            self.session.add(session)
            await self.session.commit()
            await self.session.refresh(session)
            logger.info(
                f"Added new workout session {session.id} for user {session.user_id}."
            )
            return session
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in add workout session for user {session.user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in add workout session for user {session.user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def update(self, session: WorkoutSession) -> WorkoutSession:
        try:
            await self.session.commit()
            await self.session.refresh(session)
            logger.info(f"Updated workout session {session.id}.")
            return session
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in update workout session {session.id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in update workout session {session.id}: {e}",
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
                logger.info(f"Deleted workout session {item_id}.")
            else:
                logger.warning(
                    f"Attempted to delete non-existent workout session {item_id}."
                )
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in delete workout session {item_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in delete workout session {item_id}: {e}",
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
                logger.debug(f"No active session found for user {user_id}.")
            return session
        except SQLAlchemyError as e:
            logger.error(
                f"SQLAlchemyError in get_active_session_for_user {user_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_active_session_for_user {user_id}: {e}",
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
                f"SQLAlchemyError in start_session for user {user_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in start_session for user {user_id}: {e}",
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
                f"SQLAlchemyError in end_session for session {session_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in end_session for session {session_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
