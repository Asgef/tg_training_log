"""Handler для тренировок."""
import structlog
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from pydantic import ValidationError

from src.application.use_case_interfaces import IWorkoutUseCase, IMachineManagementUseCase
from src.application.dto import SetEntryInputDTO
from src.infrastructure.web.handlers.workout_keyboards import (
    build_machine_selection_keyboard,
    build_set_params_keyboard,
)
from src.infrastructure.web.handlers.registration import build_main_menu

logger = structlog.get_logger(__name__)

router = Router()

class WorkoutStates(StatesGroup):
    choosing_machine = State()
    searching_machine = State()
    editing_set_params = State()
    manual_weight_input = State()
    manual_reps_input = State()


RECENT_MACHINES_LIMIT = 5
DEFAULT_REPS = 8
DEFAULT_RIR = 2


def _format_weight(weight: float) -> str:
    if float(weight).is_integer():
        return str(int(weight))
    return f"{weight:.2f}".rstrip("0").rstrip(".")


def _build_set_params_text(weight: float, reps: int, rir: int) -> str:
    lines = [
        "📝 Укажи параметры подхода:",
        "🟢 Тренировка активна — подход будет сохранён в текущую сессию.",
        "",
        f"💪 Вес: {_format_weight(weight)} кг",
        f"🔁 Повторы: {reps}",
        f"🧠 RIR: {rir}",
    ]
    return "\n".join(lines)


def _build_cancel_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Строит клавиатуру подтверждения отмены тренировки."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Да, удалить всё", callback_data="workout_cancel_confirm"
            ),
            InlineKeyboardButton(text="❌ Отмена", callback_data="workout_cancel_abort"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def _order_machines(machines, recent_ids: list[int]):
    machines_by_id = {machine.id: machine for machine in machines}
    recent = [machines_by_id[mid] for mid in recent_ids if mid in machines_by_id]
    recent_set = set(recent_ids)
    others = sorted(
        [machine for machine in machines if machine.id not in recent_set],
        key=lambda machine: machine.name.casefold(),
    )
    return recent, others


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
                event_type="workout_started",
                user_id=user_id,
                session_id=session.id,
            )
            await message.answer(
                "Тренировка начата! Теперь вы можете записывать подходы.",
                reply_markup=build_main_menu(True),
            )
        else:
            logger.warning(
                "Пользователь не смог начать новую тренировку; активная сессия уже существует",
                event_type="workout_start_failed",
                user_id=user_id,
                reason="active_session_exists",
            )
            await message.answer(
                "У вас уже есть активная тренировка. Завершите ее, прежде чем начинать новую."
            )
    except ValueError as e:
        logger.warning(
            "Пользователь не может начать тренировку",
            event_type="workout_start_validation_error",
            user_id=message.from_user.id,
            error=str(e),
        )
        await message.answer(str(e))
    except Exception as e:
        logger.error(
            "Ошибка в cmd_workout_start",
            event_type="workout_start_error",
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
        has_sets = await workout_use_case.has_sets_in_active_workout(user_id)
        if not has_sets:
            await message.answer(
                "В этой тренировке нет подходов. Добавьте подходы или отмените тренировку."
            )
            return

        session = await workout_use_case.end_current_workout(user_id)
        if session:
            logger.info(
                "Пользователь успешно завершил тренировку",
                event_type="workout_ended",
                user_id=user_id,
                session_id=session.id,
            )
            await message.answer(
                "Тренировка завершена! Все подходы сохранены.",
                reply_markup=build_main_menu(False),
            )
        else:
            logger.warning(
                "Пользователь не смог завершить тренировку; активная сессия не найдена",
                event_type="workout_end_failed",
                user_id=user_id,
                reason="no_active_session",
            )
            await message.answer("У вас нет активной тренировки для завершения.")
    except Exception as e:
        logger.error(
            "Ошибка в cmd_workout_end",
            event_type="workout_end_error",
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
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик команды /record_set."""
    try:
        await state.clear()
        user_id = message.from_user.id
        active_session = await workout_use_case.get_active_workout_session(user_id)
        if not active_session:
            logger.warning(
                "Пользователь попытался записать подход без активной тренировки",
                event_type="set_record_attempt_no_session",
                user_id=user_id,
            )
            await message.answer("Для записи подхода сначала начните тренировку (команда /workout_start).")
            return

        machines = await machine_management_use_case.get_user_machines(user_id)
        if not machines:
            await message.answer(
                "У вас нет тренажёров. Сначала добавьте тренажёр в меню 'Тренажеры'."
            )
            return

        recent_ids = await workout_use_case.get_recent_machine_ids(
            user_id=user_id,
            limit=RECENT_MACHINES_LIMIT,
        )
        recent, others = _order_machines(machines, recent_ids)
        keyboard = build_machine_selection_keyboard(recent, others)
        sent_message = await message.answer("🏋️ Выбери тренажёр:", reply_markup=keyboard)
        await state.set_state(WorkoutStates.choosing_machine)
        await state.update_data(
            machine_select_message_id=sent_message.message_id,
            recent_ids=recent_ids,
        )
        logger.info(
            "Пользователь перешёл в состояние choosing_machine",
            event_type="machine_select_state_entered",
            user_id=user_id,
        )
    except Exception as e:
        logger.error(
            "Ошибка в cmd_record_set",
            event_type="set_record_preparation_error",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True,
        )
        await message.answer("Произошла ошибка при подготовке к записи подхода.")

@router.callback_query(F.data == "machine_search", WorkoutStates.choosing_machine)
async def handle_machine_search(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Запрашивает ввод части названия тренажёра."""
    await state.set_state(WorkoutStates.searching_machine)
    await callback.message.edit_text("Введите часть названия тренажёра:")
    await callback.answer()


@router.message(WorkoutStates.searching_machine)
async def handle_machine_search_input(
    message: Message,
    state: FSMContext,
    workout_use_case: IWorkoutUseCase,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик ввода для поиска тренажёра."""
    user_id = message.from_user.id
    query = message.text.strip().casefold()
    data = await state.get_data()
    message_id = data.get("machine_select_message_id")

    machines = await machine_management_use_case.get_user_machines(user_id)
    recent_ids = data.get("recent_ids") or await workout_use_case.get_recent_machine_ids(
        user_id=user_id,
        limit=RECENT_MACHINES_LIMIT,
    )

    matches = [m for m in machines if query in m.name.casefold()]
    if matches:
        recent, others = _order_machines(matches, recent_ids)
        text = "🏋️ Выбери тренажёр:"
        keyboard = build_machine_selection_keyboard(recent, others)
    else:
        recent, others = _order_machines(machines, recent_ids)
        text = "Ничего не найдено. Выберите тренажёр из списка:"
        keyboard = build_machine_selection_keyboard(recent, others)

    if message_id:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=text,
            reply_markup=keyboard,
        )
    await state.set_state(WorkoutStates.choosing_machine)


@router.callback_query(F.data.startswith("machine_select:"), WorkoutStates.choosing_machine)
async def handle_machine_select(
    callback: CallbackQuery,
    state: FSMContext,
    workout_use_case: IWorkoutUseCase,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик выбора тренажёра."""
    try:
        machine_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("Некорректный тренажёр.", show_alert=True)
        return

    user_id = callback.from_user.id
    machine = await machine_management_use_case.get_machine_details(user_id, machine_id)
    if not machine:
        await callback.answer("Тренажёр не найден.", show_alert=True)
        return

    last_set = await workout_use_case.get_last_set_for_machine(user_id, machine_id)
    if last_set:
        weight = float(last_set.weight)
        reps = last_set.reps
        rir = last_set.rir
    else:
        weight = 0.0
        reps = DEFAULT_REPS
        rir = DEFAULT_RIR

    await state.set_state(WorkoutStates.editing_set_params)
    await state.update_data(
        machine_id=machine_id,
        machine_name=machine.name,
        weight=weight,
        reps=reps,
        rir=rir,
        default_weight=weight,
        default_reps=reps,
        default_rir=rir,
        form_message_id=callback.message.message_id,
    )

    await callback.message.edit_text(
        _build_set_params_text(weight, reps, rir),
        reply_markup=build_set_params_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_weight:"), WorkoutStates.editing_set_params)
async def handle_weight_change(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменяет вес по кнопкам."""
    data = await state.get_data()
    current_weight = float(data.get("weight", 0.0))
    try:
        delta = float(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("Некорректное значение веса.", show_alert=True)
        return

    new_weight = max(0.0, round(current_weight + delta, 2))
    await state.update_data(weight=new_weight)
    await callback.message.edit_text(
        _build_set_params_text(new_weight, data.get("reps", DEFAULT_REPS), data.get("rir", DEFAULT_RIR)),
        reply_markup=build_set_params_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "set_manual_weight", WorkoutStates.editing_set_params)
async def handle_manual_weight_request(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрашивает ручной ввод веса."""
    await state.set_state(WorkoutStates.manual_weight_input)
    await callback.message.answer("Введите вес одним числом (например, 80.5).")
    await callback.answer()


@router.message(WorkoutStates.manual_weight_input)
async def handle_manual_weight_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ручной ввод веса."""
    data = await state.get_data()
    raw = message.text.replace(",", ".").strip()
    try:
        weight = float(raw)
        if weight <= 0:
            raise ValueError("Вес должен быть больше 0")
    except ValueError:
        await message.answer("Введите корректный вес больше 0.")
        return

    await state.update_data(weight=weight)
    await state.set_state(WorkoutStates.editing_set_params)
    message_id = data.get("form_message_id")
    if message_id:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=_build_set_params_text(weight, data.get("reps", DEFAULT_REPS), data.get("rir", DEFAULT_RIR)),
            reply_markup=build_set_params_keyboard(),
        )


@router.callback_query(F.data.startswith("set_reps:"), WorkoutStates.editing_set_params)
async def handle_reps_change(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменяет количество повторений по кнопкам."""
    data = await state.get_data()
    try:
        reps_value = callback.data.split(":")[-1]
        if reps_value.startswith(("+", "-")):
            delta = int(reps_value)
            current_reps = int(data.get("reps", DEFAULT_REPS))
            reps = max(1, current_reps + delta)
        else:
            reps = int(reps_value)
    except ValueError:
        await callback.answer("Некорректное число повторений.", show_alert=True)
        return

    await state.update_data(reps=reps)
    await callback.message.edit_text(
        _build_set_params_text(data.get("weight", 0.0), reps, data.get("rir", DEFAULT_RIR)),
        reply_markup=build_set_params_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "set_manual_reps", WorkoutStates.editing_set_params)
async def handle_manual_reps_request(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрашивает ручной ввод повторений."""
    await state.set_state(WorkoutStates.manual_reps_input)
    await callback.message.answer("Введите количество повторений целым числом (например, 8).")
    await callback.answer()


@router.message(WorkoutStates.manual_reps_input)
async def handle_manual_reps_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ручной ввод повторений."""
    data = await state.get_data()
    try:
        reps = int(message.text.strip())
        if reps <= 0:
            raise ValueError("Повторы должны быть больше 0")
    except ValueError:
        await message.answer("Введите корректное число повторений больше 0.")
        return

    await state.update_data(reps=reps)
    await state.set_state(WorkoutStates.editing_set_params)
    message_id = data.get("form_message_id")
    if message_id:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=_build_set_params_text(data.get("weight", 0.0), reps, data.get("rir", DEFAULT_RIR)),
            reply_markup=build_set_params_keyboard(),
        )


@router.callback_query(F.data.startswith("set_rir:"), WorkoutStates.editing_set_params)
async def handle_rir_change(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменяет значение RIR."""
    data = await state.get_data()
    try:
        rir_value = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("Некорректное значение RIR.", show_alert=True)
        return

    if rir_value < 0 or rir_value > 5:
        await callback.answer("RIR должен быть в диапазоне 0..5.", show_alert=True)
        return

    await state.update_data(rir=rir_value)
    await callback.message.edit_text(
        _build_set_params_text(data.get("weight", 0.0), data.get("reps", DEFAULT_REPS), rir_value),
        reply_markup=build_set_params_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "set_reset", WorkoutStates.editing_set_params)
async def handle_set_reset(callback: CallbackQuery, state: FSMContext) -> None:
    """Сбрасывает параметры к значениям по умолчанию."""
    data = await state.get_data()
    weight = float(data.get("default_weight", 0.0))
    reps = int(data.get("default_reps", DEFAULT_REPS))
    rir = int(data.get("default_rir", DEFAULT_RIR))
    await state.update_data(weight=weight, reps=reps, rir=rir)
    await callback.message.edit_text(
        _build_set_params_text(weight, reps, rir),
        reply_markup=build_set_params_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "set_cancel", WorkoutStates.editing_set_params)
async def handle_set_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменяет ввод подхода."""
    await state.clear()
    await callback.message.edit_text("Ввод подхода отменён.")
    await callback.answer()


@router.callback_query(F.data == "set_save", WorkoutStates.editing_set_params)
async def handle_set_save(
    callback: CallbackQuery,
    state: FSMContext,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Сохраняет подход."""
    user_id = callback.from_user.id
    data = await state.get_data()
    machine_id = data.get("machine_id")
    weight = float(data.get("weight", 0.0))
    reps = int(data.get("reps", 0))
    rir = int(data.get("rir", DEFAULT_RIR))

    try:
        set_input = SetEntryInputDTO(
            machine_id=machine_id,
            weight=weight,
            reps=reps,
            rir=rir,
        )
    except ValidationError as e:
        error_messages = "; ".join([err["msg"] for err in e.errors()])
        await callback.answer(f"Ошибка: {error_messages}", show_alert=True)
        return

    try:
        set_entry = await workout_use_case.record_set(
            user_id,
            set_input.machine_id,
            set_input.weight,
            set_input.reps,
            set_input.rir,
        )
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
        return

    if not set_entry:
        await callback.answer("Не удалось записать подход. Проверьте тренировку.", show_alert=True)
        return

    machine_name = data.get("machine_name") or f"ID {set_input.machine_id}"
    await state.clear()
    await callback.message.edit_text(
        f"✅ Подход записан: {machine_name} — {_format_weight(set_input.weight)} кг × {set_input.reps}, RIR: {set_input.rir}."
    )
    await callback.answer()


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
                event_type="workout_started",
                user_id=user_id,
                session_id=session.id,
                source="button",
            )
            await message.answer(
                "Тренировка начата! Теперь вы можете записывать подходы.",
                reply_markup=build_main_menu(True),
            )
        else:
            logger.warning(
                "Пользователь не смог начать новую тренировку через кнопку; активная сессия уже существует",
                event_type="workout_start_failed",
                user_id=user_id,
                reason="active_session_exists",
                source="button",
            )
            await message.answer("У вас уже есть активная тренировка. Завершите ее, прежде чем начинать новую.")
    except ValueError as e:
        logger.warning(
            "Пользователь не может начать тренировку через кнопку",
            event_type="workout_start_validation_error",
            user_id=message.from_user.id,
            error=str(e),
            source="button",
        )
        await message.answer(str(e))
    except Exception as e:
        logger.error(
            "Ошибка в handle_start_workout_button",
            event_type="workout_start_error",
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


@router.message(F.text == "❌ Отменить тренировку")
async def handle_cancel_workout_button(
    message: Message,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Обработчик кнопки 'Отменить тренировку'."""
    user_id = message.from_user.id
    active_session = await workout_use_case.get_active_workout_session(user_id)
    if not active_session:
        await message.answer("У вас нет активной тренировки для отмены.")
        return

    has_sets = await workout_use_case.has_sets_in_active_workout(user_id)
    if not has_sets:
        success = await workout_use_case.cancel_current_workout(user_id)
        if success:
            await message.answer(
                "Тренировка отменена.",
                reply_markup=build_main_menu(False),
            )
        else:
            await message.answer("Не удалось отменить тренировку. Попробуйте позже.")
        return

    warning_text = (
        "⚠️ У тебя уже есть подходы в этой тренировке.\n"
        "Если ты отменишь тренировку, все они будут удалены.\n\n"
        "❗ Продолжить?"
    )
    await message.answer(
        warning_text,
        reply_markup=_build_cancel_confirmation_keyboard(),
    )


@router.callback_query(F.data == "workout_cancel_confirm")
async def handle_cancel_workout_confirm(
    callback: CallbackQuery,
    workout_use_case: IWorkoutUseCase,
) -> None:
    """Подтверждение отмены тренировки."""
    user_id = callback.from_user.id
    success = await workout_use_case.cancel_current_workout(user_id)
    if success:
        await callback.message.edit_text("Тренировка отменена. Все подходы удалены.")
        await callback.message.answer(
            "Главное меню:",
            reply_markup=build_main_menu(False),
        )
        await callback.answer()
    else:
        await callback.answer("Не удалось отменить тренировку.", show_alert=True)


@router.callback_query(F.data == "workout_cancel_abort")
async def handle_cancel_workout_abort(callback: CallbackQuery) -> None:
    """Отмена подтверждения отмены тренировки."""
    await callback.message.edit_text("Тренировка продолжается")
    await callback.answer()


@router.message(F.text == "📝 Записать подход")
async def handle_record_set_button(
    message: Message,
    state: FSMContext,
    workout_use_case: IWorkoutUseCase,
    machine_management_use_case: IMachineManagementUseCase,
) -> None:
    """Обработчик кнопки 'Записать подход'."""
    await cmd_record_set(message, state, workout_use_case, machine_management_use_case)