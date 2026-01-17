import structlog
from typing import Optional
from src.application.repositories import IWorkoutSessionRepository, ISetEntryRepository, IMachineRepository
from src.application.use_case_interfaces import IWorkoutUseCase
from src.domain.models import WorkoutSession, SetEntry
from src.application.dto import (
    WorkoutSessionDTO,
    SetEntryDTO,
    workout_session_to_dto,
    set_entry_to_dto,
)

logger = structlog.get_logger(__name__)


class WorkoutUseCase(IWorkoutUseCase):
    def __init__(
        self,
        workout_session_repository: IWorkoutSessionRepository,
        set_entry_repository: ISetEntryRepository,
        machine_repository: IMachineRepository,
    ):
        self.workout_session_repository = workout_session_repository
        self.set_entry_repository = set_entry_repository
        self.machine_repository = machine_repository

    async def start_new_workout(self, user_id: int) -> Optional[WorkoutSessionDTO]:
        try:
            # Проверка наличия тренажеров у пользователя
            machines = await self.machine_repository.get_user_machines(
                user_id, include_archived=False
            )
            if not machines:
                logger.warning(
                    "Пользователь попытался начать тренировку, но у него нет тренажеров.",
                    user_id=user_id,
                )
                raise ValueError("У вас нет тренажеров. Вы не можете начать тренировку. Сначала добавьте тренажеры в меню 'Тренажеры'.")

            active_session = (
                await self.workout_session_repository.get_active_session_for_user(
                    user_id
                )
            )
            if active_session:
                logger.info(
                    "Пользователь попытался начать новую тренировку, но уже имеет активную сессию.",
                    user_id=user_id,
                    active_session_id=active_session.id,
                )
                return None

            new_session = await self.workout_session_repository.start_session(user_id)
            logger.info("Пользователь начал новую тренировку.", user_id=user_id, session_id=new_session.id)
            return workout_session_to_dto(new_session)
        except ValueError:
            # Пробрасываем ValueError дальше, чтобы хэндлер мог обработать его
            raise
        except Exception as e:
            logger.error("Ошибка при начале новой тренировки", user_id=user_id, error=str(e), exc_info=True)
            return None

    async def end_current_workout(self, user_id: int) -> Optional[WorkoutSessionDTO]:
        try:
            active_session = (
                await self.workout_session_repository.get_active_session_for_user(
                    user_id
                )
            )
            if not active_session:
                logger.info(
                    "Пользователь попытался завершить тренировку, но не имеет активной сессии.",
                    user_id=user_id,
                )
                return None

            await self.workout_session_repository.end_session(active_session.id)
            ended_session = await self.workout_session_repository.get_by_id(
                active_session.id
            )
            logger.info("Пользователь завершил тренировку.", user_id=user_id, session_id=active_session.id)
            return workout_session_to_dto(ended_session)
        except Exception as e:
            logger.error("Ошибка при завершении тренировки", user_id=user_id, error=str(e), exc_info=True)
            return None

    async def record_set(
        self, user_id: int, machine_id: int, weight: float, reps: int, rir: int
    ) -> Optional[SetEntryDTO]:
        try:
            active_session = (
                await self.workout_session_repository.get_active_session_for_user(
                    user_id
                )
            )
            if not active_session:
                logger.warning(
                    "Пользователь попытался записать подход, но не имеет активной сессии.",
                    user_id=user_id,
                )
                return None

            # Проверка существования тренажера и принадлежности пользователю
            machine = await self.machine_repository.get_by_id(machine_id)
            if not machine:
                logger.warning(
                    "Пользователь попытался записать подход на несуществующий тренажер.",
                    user_id=user_id,
                    machine_id=machine_id,
                )
                raise ValueError(f"Тренажер с ID {machine_id} не найден.")
            
            if machine.user_id != user_id:
                logger.warning(
                    "Пользователь попытался записать подход на тренажер, принадлежащий другому пользователю.",
                    user_id=user_id,
                    machine_id=machine_id,
                    machine_owner_id=machine.user_id,
                )
                raise ValueError(f"Тренажер с ID {machine_id} не принадлежит вам.")
            
            if machine.is_archived:
                logger.warning(
                    "Пользователь попытался записать подход на архивированный тренажер.",
                    user_id=user_id,
                    machine_id=machine_id,
                )
                raise ValueError(f"Тренажер с ID {machine_id} архивирован и недоступен для записи подходов.")

            # Валидация weight и reps уже выполнена на уровне DTO в handlers
            # Здесь оставляем только бизнес-валидацию

            new_set_entry = SetEntry(
                session_id=active_session.id,
                machine_id=machine_id,
                weight=weight,
                reps=reps,
                rir=rir,
            )
            await self.set_entry_repository.add_set_entry(new_set_entry)
            zone_ids = [zone.id for zone in machine.zones] if machine.zones else []
            muscle_ids = [muscle.id for muscle in machine.muscles] if machine.muscles else []
            await self.set_entry_repository.add_set_entry_snapshots(
                new_set_entry.id, zone_ids, muscle_ids
            )
            logger.info(
                "Пользователь записал подход.",
                user_id=user_id,
                set_entry_id=new_set_entry.id,
                session_id=active_session.id,
                machine_id=machine_id,
                weight=weight,
                reps=reps,
            )
            return set_entry_to_dto(new_set_entry)
        except ValueError:
            # Пробрасываем ValueError дальше, чтобы хэндлер мог обработать его
            raise
        except Exception as e:
            logger.error("Ошибка при записи подхода", user_id=user_id, error=str(e), exc_info=True)
            return None

    async def get_active_workout_session(
        self, user_id: int
    ) -> Optional[WorkoutSessionDTO]:
        try:
            session = await self.workout_session_repository.get_active_session_for_user(
                user_id
            )
            if session:
                return workout_session_to_dto(session)
            return None
        except Exception as e:
            logger.error(
                "Ошибка при получении активной тренировки",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            return None

    async def get_recent_machine_ids(self, user_id: int, limit: int = 5) -> list[int]:
        try:
            return await self.set_entry_repository.get_recent_machine_ids(
                user_id=user_id,
                limit=limit,
            )
        except Exception as e:
            logger.error(
                "Ошибка при получении последних тренажёров",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            return []

    async def get_last_set_for_machine(
        self, user_id: int, machine_id: int
    ) -> Optional[SetEntryDTO]:
        try:
            last_set = await self.set_entry_repository.get_last_set_for_machine(
                user_id=user_id,
                machine_id=machine_id,
            )
            if last_set:
                return set_entry_to_dto(last_set)
            return None
        except Exception as e:
            logger.error(
                "Ошибка при получении последнего подхода по тренажёру",
                user_id=user_id,
                machine_id=machine_id,
                error=str(e),
                exc_info=True,
            )
            return None

    async def has_sets_in_active_workout(self, user_id: int) -> bool:
        try:
            active_session = (
                await self.workout_session_repository.get_active_session_for_user(
                    user_id
                )
            )
            if not active_session:
                return False
            return await self.set_entry_repository.has_entries_for_session(
                active_session.id
            )
        except Exception as e:
            logger.error(
                "Ошибка при проверке подходов в активной тренировке",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            return False

    async def cancel_current_workout(self, user_id: int) -> bool:
        try:
            active_session = (
                await self.workout_session_repository.get_active_session_for_user(
                    user_id
                )
            )
            if not active_session:
                logger.info(
                    "Пользователь попытался отменить тренировку без активной сессии.",
                    user_id=user_id,
                )
                return False

            await self.set_entry_repository.delete_by_session_id(active_session.id)
            await self.workout_session_repository.delete(active_session.id)
            logger.info(
                "Пользователь отменил тренировку.",
                user_id=user_id,
                session_id=active_session.id,
            )
            return True
        except Exception as e:
            logger.error(
                "Ошибка при отмене тренировки",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            return False
