"""Handler для тренировок."""
import structlog
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.application.use_case_interfaces import IWorkoutUseCase

logger = structlog.get_logger(__name__)

router = Router()

class WorkoutStates(StatesGroup):
    choosing_machine = State()
    waiting_for_set_data = State()


@router.message(Command("workout_start"))
async def cmd_workout_start(
    message: Message,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Обработчик команды /workout_start."""
    try:
        user_id = message.from_user.id
        session = await workout_use_case.start_new_workout(user_id)
        if session:
            logger.info(
                "Пользователь успешно начал новую тренировку",
                event="workout_started",
                user_id=user_id,
                session_id=session.id,
            )
            await message.answer("Тренировка начата! Теперь вы можете записывать подходы.")
        else:
            logger.warning(
                "Пользователь не смог начать новую тренировку; активная сессия уже существует",
                event="workout_start_failed",
                user_id=user_id,
                reason="active_session_exists",
            )
            await message.answer("У вас уже есть активная тренировка. Завершите ее, прежде чем начинать новую.")
    except ValueError as e:
        logger.warning(
            "Пользователь не может начать тренировку",
            event="workout_start_validation_error",
            user_id=message.from_user.id,
            error=str(e),
        )
        await message.answer(str(e))
    except Exception as e:
        logger.error(
            "Ошибка в cmd_workout_start",
            event="workout_start_error",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await message.answer("Произошла ошибка при начале тренировки.")

@router.message(Command("workout_end"))
async def cmd_workout_end(
    message: Message,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Обработчик команды /workout_end."""
    try:
        user_id = message.from_user.id
        session = await workout_use_case.end_current_workout(user_id)
        if session:
            logger.info(
                "Пользователь успешно завершил тренировку",
                event="workout_ended",
                user_id=user_id,
                session_id=session.id,
            )
            await message.answer("Тренировка завершена! Все подходы сохранены.")
        else:
            logger.warning(
                "Пользователь не смог завершить тренировку; активная сессия не найдена",
                event="workout_end_failed",
                user_id=user_id,
                reason="no_active_session",
            )
            await message.answer("У вас нет активной тренировки для завершения.")
    except Exception as e:
        logger.error(
            "Ошибка в cmd_workout_end",
            event="workout_end_error",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await message.answer("Произошла ошибка при завершении тренировки.")

@router.message(Command("record_set"))
async def cmd_record_set(
    message: Message,
    state: FSMContext,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Обработчик команды /record_set."""
    try:
        user_id = message.from_user.id
        active_session = await workout_use_case.get_active_workout_session(user_id)
        if not active_session:
            logger.warning(
                "Пользователь попытался записать подход без активной тренировки",
                event="set_record_attempt_no_session",
                user_id=user_id,
            )
            await message.answer("Для записи подхода сначала начните тренировку (команда /workout_start).")
            return

        await message.answer("Введите данные подхода в формате: `machine_id вес повторы отказ(0/1)`.\nНапример: `1 100 8 0` (machine_id=1, вес=100кг, 8 повторений, без отказа).")
        await state.set_state(WorkoutStates.waiting_for_set_data)
        logger.info(
            "Пользователь перешёл в состояние waiting_for_set_data",
            event="set_record_state_entered",
            user_id=user_id,
        )
    except Exception as e:
        logger.error(
            "Ошибка в cmd_record_set",
            event="set_record_preparation_error",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await message.answer("Произошла ошибка при подготовке к записи подхода.")

@router.message(WorkoutStates.waiting_for_set_data)
async def process_set_data(
    message: Message,
    state: FSMContext,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Обработчик ввода данных подхода."""
    user_id = message.from_user.id
    try:
        parts = message.text.split()
        if len(parts) != 4:
            raise ValueError("Неверный формат. Пожалуйста, используйте: `machine_id вес повторы отказ(0/1)`")

        machine_id = int(parts[0])
        weight = float(parts[1])
        reps = int(parts[2])
        failure = bool(int(parts[3]))

        set_entry = await workout_use_case.record_set(user_id, machine_id, weight, reps, failure)
        if set_entry:
            logger.info(
                "Пользователь успешно записал подход",
                event="set_recorded",
                user_id=user_id,
                set_entry_id=set_entry.id,
                machine_id=machine_id,
                weight=weight,
                reps=reps,
                failure=failure,
            )
            await message.answer(f"Подход записан: {weight}кг x {reps} на тренажере {machine_id}.")
        else:
            logger.warning(
                "Пользователь не смог записать подход",
                event="set_record_failed",
                user_id=user_id,
                machine_id=machine_id,
                weight=weight,
                reps=reps,
                failure=failure,
            )
            await message.answer("Не удалось записать подход. Убедитесь, что у вас активна тренировка и данные верны.")
    except ValueError as e:
        logger.warning(
            "Пользователь предоставил неверный формат данных подхода",
            event="set_record_validation_error",
            user_id=user_id,
            input_text=message.text,
            error=str(e),
        )
        await message.answer(f"Ошибка в формате данных: {e}. Попробуйте еще раз.")
    except Exception as e:
        logger.error(
            "Неожиданная ошибка в process_set_data",
            event="set_record_error",
            user_id=user_id,
            input_text=message.text,
            error=str(e),
            exc_info=True,
        )
        await message.answer(f"Произошла ошибка при записи подхода: {e}")
    finally:
        await state.clear()


# Обработчики кнопок меню
@router.message(F.text == "🏋️ Начать тренировку")
async def handle_start_workout_button(
    message: Message,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Обработчик кнопки 'Начать тренировку'."""
    try:
        user_id = message.from_user.id
        session = await workout_use_case.start_new_workout(user_id)
        if session:
            logger.info(
                "Пользователь успешно начал новую тренировку через кнопку",
                event="workout_started",
                user_id=user_id,
                session_id=session.id,
                source="button",
            )
            await message.answer("Тренировка начата! Теперь вы можете записывать подходы.")
        else:
            logger.warning(
                "Пользователь не смог начать новую тренировку через кнопку; активная сессия уже существует",
                event="workout_start_failed",
                user_id=user_id,
                reason="active_session_exists",
                source="button",
            )
            await message.answer("У вас уже есть активная тренировка. Завершите ее, прежде чем начинать новую.")
    except ValueError as e:
        logger.warning(
            "Пользователь не может начать тренировку через кнопку",
            event="workout_start_validation_error",
            user_id=message.from_user.id,
            error=str(e),
            source="button",
        )
        await message.answer(str(e))
    except Exception as e:
        logger.error(
            "Ошибка в handle_start_workout_button",
            event="workout_start_error",
            user_id=message.from_user.id,
            error=str(e),
            source="button",
            exc_info=True,
        )
        await message.answer("Произошла ошибка при начале тренировки.")


@router.message(F.text == "✅ Завершить тренировку")
async def handle_end_workout_button(
    message: Message,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Обработчик кнопки 'Завершить тренировку'."""
    await cmd_workout_end(message, workout_use_case)


@router.message(F.text == "📝 Записать подход")
async def handle_record_set_button(
    message: Message,
    state: FSMContext,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Обработчик кнопки 'Записать подход'."""
    await cmd_record_set(message, state, workout_use_case)