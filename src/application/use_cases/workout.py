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
                    f"Пользователь {user_id} попытался начать новую тренировку, но уже имеет активную сессию."
                )
                return None

            new_session = await self.workout_session_repository.start_session(user_id)
            logger.info(f"Пользователь {user_id} начал новую тренировку {new_session.id}.")
            return new_session
        except Exception as e:
            logger.error(f"Ошибка при начале новой тренировки для пользователя {user_id}: {e}")
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
                    f"Пользователь {user_id} попытался завершить тренировку, но не имеет активной сессии."
                )
                return None

            await self.workout_session_repository.end_session(active_session.id)
            ended_session = await self.workout_session_repository.get_by_id(
                active_session.id
            )
            logger.info(f"Пользователь {user_id} завершил тренировку {active_session.id}.")
            return ended_session
        except Exception as e:
            logger.error(f"Ошибка при завершении тренировки для пользователя {user_id}: {e}")
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
                    f"Пользователь {user_id} попытался записать подход, но не имеет активной сессии."
                )
                return None

            if weight <= 0 or reps <= 0:
                logger.warning(
                    f"Пользователь {user_id} предоставил неверные данные подхода: вес={weight}, повторы={reps}."
                )
                raise ValueError("Вес и повторы должны быть больше 0")

            new_set_entry = SetEntry(
                session_id=active_session.id,
                machine_id=machine_id,
                weight=weight,
                reps=reps,
                failure=failure,
            )
            await self.set_entry_repository.add_set_entry(new_set_entry)
            logger.info(
                f"Пользователь {user_id} записал подход {new_set_entry.id} для сессии {active_session.id}."
            )
            return new_set_entry
        except Exception as e:
            logger.error(f"Ошибка при записи подхода для пользователя {user_id}: {e}")
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
                f"Ошибка при получении активной тренировки для пользователя {user_id}: {e}"
            )
            return None
