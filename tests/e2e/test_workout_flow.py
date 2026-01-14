"""E2E тесты для потока тренировок."""
import pytest
from src.domain.models import User, Machine
from src.infrastructure.web.handlers import workout

from tests.e2e.conftest import create_message_update


@pytest.mark.e2e
async def test_start_workout_flow(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест начала тренировки."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()
    
    # Пользователь отправляет команду /workout_start
    update = create_message_update("/workout_start", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что тренировка начата
    workout_repo = container.workout_session_repository()
    active_session = await workout_repo.get_active_session_for_user(test_user_id)
    assert active_session is not None
    
    # Проверяем, что бот отправил подтверждение
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "начата" in call_args.kwargs["text"].lower() or "начал" in call_args.kwargs["text"].lower()


@pytest.mark.e2e
async def test_start_workout_button(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест начала тренировки через кнопку меню."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()
    
    # Пользователь нажимает кнопку "🏋️ Начать тренировку"
    update = create_message_update("🏋️ Начать тренировку", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что тренировка начата
    workout_repo = container.workout_session_repository()
    active_session = await workout_repo.get_active_session_for_user(test_user_id)
    assert active_session is not None
    
    # Проверяем, что бот отправил подтверждение
    assert bot.send_message.called


@pytest.mark.e2e
async def test_start_workout_when_active_exists(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест попытки начать тренировку, когда уже есть активная."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()
    
    # Начинаем первую тренировку
    workout_repo = container.workout_session_repository()
    await workout_repo.start_session(test_user_id)
    await test_session.commit()
    
    # Пытаемся начать вторую тренировку
    update = create_message_update("/workout_start", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что бот сообщил об ошибке
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "уже есть" in call_args.kwargs["text"].lower() or "активная" in call_args.kwargs["text"].lower()


@pytest.mark.e2e
async def test_end_workout_flow(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест завершения тренировки."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()
    
    # Начинаем тренировку
    workout_repo = container.workout_session_repository()
    session = await workout_repo.start_session(test_user_id)
    await test_session.commit()
    
    # Пользователь завершает тренировку
    update = create_message_update("/workout_end", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что тренировка завершена
    await test_session.refresh(session)
    assert session.ended_at is not None
    
    # Проверяем, что бот отправил подтверждение
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "завершена" in call_args.kwargs["text"].lower() or "завершена" in call_args.kwargs["text"].lower()


@pytest.mark.e2e
async def test_end_workout_without_active(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест попытки завершить тренировку без активной."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()
    
    # Пытаемся завершить тренировку без активной
    update = create_message_update("/workout_end", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что бот сообщил об ошибке
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "нет активной" in call_args.kwargs["text"].lower() or "нет тренировки" in call_args.kwargs["text"].lower()


@pytest.mark.e2e
async def test_record_set_flow(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест записи подхода."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()
    
    # Создаём тренажёр
    machine = Machine(name="Test Machine", user_id=test_user_id)
    await container.machine_repository().add(machine)
    await test_session.commit()
    
    # Начинаем тренировку
    workout_repo = container.workout_session_repository()
    session = await workout_repo.start_session(test_user_id)
    await test_session.commit()
    
    # Пользователь запрашивает запись подхода
    update1 = create_message_update("/record_set", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update1)
    
    # Проверяем, что бот запросил данные подхода
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "формат" in call_args.kwargs["text"].lower() or "данные" in call_args.kwargs["text"].lower()
    
    # Устанавливаем состояние FSM
    from aiogram.fsm.context import FSMContext
    storage = dispatcher.storage
    state = FSMContext(storage=storage, key=storage.resolve_key(bot, test_user_id, test_user_id))
    await state.set_state(workout.WorkoutStates.waiting_for_set_data)
    
    # Пользователь отправляет данные подхода
    update2 = create_message_update(f"{machine.id} 100.0 10 0", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update2)
    
    # Проверяем, что подход записан
    set_entry_repo = container.set_entry_repository()
    # Получаем все подходы для сессии
    from sqlalchemy import select
    from src.domain.models import SetEntry
    stmt = select(SetEntry).where(SetEntry.session_id == session.id)
    result = await test_session.execute(stmt)
    entries = result.scalars().all()
    assert len(entries) > 0
    
    # Проверяем, что бот отправил подтверждение
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "записан" in call_args.kwargs["text"].lower() or "подход" in call_args.kwargs["text"].lower()


@pytest.mark.e2e
async def test_record_set_without_active_workout(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест попытки записать подход без активной тренировки."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()
    
    # Пытаемся записать подход без активной тренировки
    update = create_message_update("/record_set", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что бот сообщил об ошибке
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "начать тренировку" in call_args.kwargs["text"].lower() or "активной" in call_args.kwargs["text"].lower()
