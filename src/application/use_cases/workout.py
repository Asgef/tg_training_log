import logging
from typing import Optional
from src.application.repositories import IWorkoutSessionRepository, ISetEntryRepository
from src.application.use_cases import IWorkoutUseCase
from src.domain.models import WorkoutSession, SetEntry

logger = logging.getLogger(__name__)


class WorkoutUseCase(IWorkoutUseCase):
    def __init__(
        self,
        workout_session_repository: IWorkoutSessionRepository,
        set_entry_repository: ISetEntryRepository,
    ):
        self.workout_session_repository = workout_session_repository
        self.set_entry_repository = set_entry_repository

    async def start_new_workout(self, user_id: int) -> Optional[WorkoutSession]:
        try:
            active_session = (
                await self.workout_session_repository.get_active_session_for_user(
                    user_id
                )
            )
            if active_session:
                logger.info(
                    f"User {user_id} tried to start new workout but already has an active session."
                )
                return None

            new_session = await self.workout_session_repository.start_session(user_id)
            logger.info(f"User {user_id} started new workout session {new_session.id}.")
            return new_session
        except Exception as e:
            logger.error(f"Error starting new workout for user {user_id}: {e}")
            return None

    async def end_current_workout(self, user_id: int) -> Optional[WorkoutSession]:
        try:
            active_session = (
                await self.workout_session_repository.get_active_session_for_user(
                    user_id
                )
            )
            if not active_session:
                logger.info(
                    f"User {user_id} tried to end workout but has no active session."
                )
                return None

            await self.workout_session_repository.end_session(active_session.id)
            ended_session = await self.workout_session_repository.get_by_id(
                active_session.id
            )
            logger.info(f"User {user_id} ended workout session {active_session.id}.")
            return ended_session
        except Exception as e:
            logger.error(f"Error ending workout for user {user_id}: {e}")
            return None

    async def record_set(
        self, user_id: int, machine_id: int, weight: float, reps: int, failure: bool
    ) -> Optional[SetEntry]:
        try:
            active_session = (
                await self.workout_session_repository.get_active_session_for_user(
                    user_id
                )
            )
            if not active_session:
                logger.warning(
                    f"User {user_id} tried to record set but has no active session."
                )
                return None

            if weight <= 0 or reps <= 0:
                logger.warning(
                    f"User {user_id} provided invalid set data: weight={weight}, reps={reps}."
                )
                raise ValueError("Weight and reps must be greater than 0")

            new_set_entry = SetEntry(
                session_id=active_session.id,
                machine_id=machine_id,
                weight=weight,
                reps=reps,
                failure=failure,
            )
            await self.set_entry_repository.add_set_entry(new_set_entry)
            logger.info(
                f"User {user_id} recorded set {new_set_entry.id} for session {active_session.id}."
            )
            return new_set_entry
        except Exception as e:
            logger.error(f"Error recording set for user {user_id}: {e}")
            return None

    async def get_active_workout_session(
        self, user_id: int
    ) -> Optional[WorkoutSession]:
        try:
            return await self.workout_session_repository.get_active_session_for_user(
                user_id
            )
        except Exception as e:
            logger.error(
                f"Error getting active workout session for user {user_id}: {e}"
            )
            return None
