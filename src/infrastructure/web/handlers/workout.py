"""Handler для тренировок."""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.application.use_case_interfaces import IWorkoutUseCase

logger = logging.getLogger(__name__)

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
            logger.info(f"Пользователь {user_id} успешно начал новую тренировку {session.id}.")
            await message.answer("Тренировка начата! Теперь вы можете записывать подходы.")
        else:
            logger.warning(f"Пользователь {user_id} не смог начать новую тренировку; активная сессия уже существует.")
            await message.answer("У вас уже есть активная тренировка. Завершите ее, прежде чем начинать новую.")
    except ValueError as e:
        logger.warning(f"Пользователь {message.from_user.id} не может начать тренировку: {e}")
        await message.answer(str(e))
    except Exception as e:
        logger.error(f"Ошибка в cmd_workout_start для пользователя {message.from_user.id}: {e}", exc_info=True)
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
            logger.info(f"Пользователь {user_id} успешно завершил тренировку {session.id}.")
            await message.answer("Тренировка завершена! Все подходы сохранены.")
        else:
            logger.warning(f"Пользователь {user_id} не смог завершить тренировку; активная сессия не найдена.")
            await message.answer("У вас нет активной тренировки для завершения.")
    except Exception as e:
        logger.error(f"Ошибка в cmd_workout_end для пользователя {message.from_user.id}: {e}", exc_info=True)
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
            logger.warning(f"Пользователь {user_id} попытался записать подход без активной тренировки.")
            await message.answer("Для записи подхода сначала начните тренировку (команда /workout_start).")
            return

        await message.answer("Введите данные подхода в формате: `machine_id вес повторы отказ(0/1)`.\nНапример: `1 100 8 0` (machine_id=1, вес=100кг, 8 повторений, без отказа).")
        await state.set_state(WorkoutStates.waiting_for_set_data)
        logger.info(f"Пользователь {user_id} перешёл в состояние waiting_for_set_data.")
    except Exception as e:
        logger.error(f"Ошибка в cmd_record_set для пользователя {message.from_user.id}: {e}", exc_info=True)
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
            logger.info(f"Пользователь {user_id} успешно записал подход: тренажёр={machine_id}, вес={weight}, повторы={reps}, отказ={failure}.")
            await message.answer(f"Подход записан: {weight}кг x {reps} на тренажере {machine_id}.")
        else:
            logger.warning(f"Пользователь {user_id} не смог записать подход: тренажёр={machine_id}, вес={weight}, повторы={reps}, отказ={failure}.")
            await message.answer("Не удалось записать подход. Убедитесь, что у вас активна тренировка и данные верны.")
    except ValueError as e:
        logger.warning(f"Пользователь {user_id} предоставил неверный формат данных подхода: {message.text}. Ошибка: {e}")
        await message.answer(f"Ошибка в формате данных: {e}. Попробуйте еще раз.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в process_set_data для пользователя {user_id}, данные: {message.text}: {e}", exc_info=True)
        await message.answer(f"Произошла ошибка при записи подхода: {e}")
    finally:
        await state.clear()
        logger.debug(f"Состояние очищено для пользователя {user_id}.")


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
            logger.info(f"Пользователь {user_id} успешно начал новую тренировку {session.id}.")
            await message.answer("Тренировка начата! Теперь вы можете записывать подходы.")
        else:
            logger.warning(f"Пользователь {user_id} не смог начать новую тренировку; активная сессия уже существует.")
            await message.answer("У вас уже есть активная тренировка. Завершите ее, прежде чем начинать новую.")
    except ValueError as e:
        logger.warning(f"Пользователь {message.from_user.id} не может начать тренировку: {e}")
        await message.answer(str(e))
    except Exception as e:
        logger.error(f"Ошибка в handle_start_workout_button для пользователя {message.from_user.id}: {e}", exc_info=True)
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