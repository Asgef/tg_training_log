# ruff: noqa: F821
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


logger = logging.getLogger(__name__)

router = Router()

class WorkoutStates(StatesGroup):
    choosing_machine = State()
    waiting_for_set_data = State()


@router.message(Command("workout_start"))
async def cmd_workout_start(message: Message) -> None:
    try:
        user_id = message.from_user.id
        session = await workout_use_case.start_new_workout(user_id)
        if session:
            logger.info(f"User {user_id} successfully started a new workout session {session.id}.")
            await message.answer("Тренировка начата! Теперь вы можете записывать подходы.")
        else:
            logger.warning(f"User {user_id} failed to start new workout; active session already exists.")
            await message.answer("У вас уже есть активная тренировка. Завершите ее, прежде чем начинать новую.")
    except Exception as e:
        logger.error(f"Error in cmd_workout_start for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при начале тренировки.")

@router.message(Command("workout_end"))
async def cmd_workout_end(message: Message) -> None:
    try:
        user_id = message.from_user.id
        session = await workout_use_case.end_current_workout(user_id)
        if session:
            logger.info(f"User {user_id} successfully ended workout session {session.id}.")
            await message.answer("Тренировка завершена! Все подходы сохранены.")
        else:
            logger.warning(f"User {user_id} failed to end workout; no active session found.")
            await message.answer("У вас нет активной тренировки для завершения.")
    except Exception as e:
        logger.error(f"Error in cmd_workout_end for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при завершении тренировки.")

@router.message(Command("record_set"))
async def cmd_record_set(message: Message, state: FSMContext) -> None:
    try:
        user_id = message.from_user.id
        active_session = await workout_use_case.get_active_workout_session(user_id)
        if not active_session:
            logger.warning(f"User {user_id} tried to record set without active workout.")
            await message.answer("Для записи подхода сначала начните тренировку (команда /workout_start).")
            return

        await message.answer("Введите данные подхода в формате: `machine_id вес повторы отказ(0/1)`.\nНапример: `1 100 8 0` (machine_id=1, вес=100кг, 8 повторений, без отказа).")
        await state.set_state(WorkoutStates.waiting_for_set_data)
        logger.info(f"User {user_id} entered state waiting_for_set_data.")
    except Exception as e:
        logger.error(f"Error in cmd_record_set for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при подготовке к записи подхода.")

@router.message(WorkoutStates.waiting_for_set_data)
async def process_set_data(message: Message, state: FSMContext) -> None:
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
            logger.info(f"User {user_id} successfully recorded set: machine={machine_id}, weight={weight}, reps={reps}, failure={failure}.")
            await message.answer(f"Подход записан: {weight}кг x {reps} на тренажере {machine_id}.")
        else:
            logger.warning(f"User {user_id} failed to record set: machine={machine_id}, weight={weight}, reps={reps}, failure={failure}.")
            await message.answer("Не удалось записать подход. Убедитесь, что у вас активна тренировка и данные верны.")
    except ValueError as e:
        logger.warning(f"User {user_id} provided invalid set data format: {message.text}. Error: {e}")
        await message.answer(f"Ошибка в формате данных: {e}. Попробуйте еще раз.")
    except Exception as e:
        logger.error(f"Unexpected error in process_set_data for user {user_id}, data: {message.text}: {e}", exc_info=True)
        await message.answer(f"Произошла ошибка при записи подхода: {e}")
    finally:
        await state.clear()
        logger.debug(f"State cleared for user {user_id}.")