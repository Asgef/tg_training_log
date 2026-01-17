"""E2E тесты для потока тренировок."""
import pytest
from unittest.mock import AsyncMock
from src.domain.models import User, Machine, SetEntry
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
        telegram_id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()

    machine = Machine(name="Test Machine", user_id=test_user_id)
    await container.machine_repository().add(machine)
    await test_session.commit()
    
    # Пользователь отправляет команду /workout_start
    update = create_message_update("/workout_start", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что тренировка начата
    workout_repo = container.workout_session_repository()
    active_session = await workout_repo.get_active_session_for_user(test_user_id)
    assert active_session is not None
    


@pytest.mark.e2e
async def test_start_workout_button(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест начала тренировки через кнопку меню."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()

    machine = Machine(name="Test Machine", user_id=test_user_id)
    await container.machine_repository().add(machine)
    await test_session.commit()
    
    # Пользователь нажимает кнопку "🏋️ Начать тренировку"
    update = create_message_update("🏋️ Начать тренировку", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что тренировка начата
    workout_repo = container.workout_session_repository()
    active_session = await workout_repo.get_active_session_for_user(test_user_id)
    assert active_session is not None
    


@pytest.mark.e2e
async def test_start_workout_when_active_exists(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест попытки начать тренировку, когда уже есть активная."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()

    machine = Machine(name="Test Machine", user_id=test_user_id)
    await container.machine_repository().add(machine)
    await test_session.commit()
    
    # Начинаем первую тренировку
    workout_repo = container.workout_session_repository()
    await workout_repo.start_session(test_user_id)
    await test_session.commit()
    
    # Пытаемся начать вторую тренировку
    update = create_message_update("/workout_start", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    


@pytest.mark.e2e
async def test_end_workout_flow(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест завершения тренировки."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)
    await test_session.commit()

    machine = Machine(name="Test Machine", user_id=test_user_id)
    await container.machine_repository().add(machine)
    await test_session.commit()
    
    # Начинаем тренировку
    workout_repo = container.workout_session_repository()
    session = await workout_repo.start_session(test_user_id)
    await test_session.commit()

    set_entry = SetEntry(
        session_id=session.id,
        machine_id=machine.id,
        weight=100.0,
        reps=10,
        rir=2,
    )
    await container.set_entry_repository().add(set_entry)
    await test_session.commit()
    
    # Пользователь завершает тренировку
    update = create_message_update("/workout_end", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что тренировка завершена
    ended_session = await container.workout_session_repository().get_by_id(session.id)
    assert ended_session is not None
    assert ended_session.ended_at is not None
    


@pytest.mark.e2e
async def test_end_workout_without_active(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест попытки завершить тренировку без активной."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
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
    


@pytest.mark.e2e
async def test_record_set_flow(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест записи подхода."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
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
    
    
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey
    storage = dispatcher.storage
    key = StorageKey(bot_id=bot.id or 0, chat_id=test_user_id, user_id=test_user_id)
    state = FSMContext(storage=storage, key=key)
    assert await state.get_state() == workout.WorkoutStates.choosing_machine.state
    


@pytest.mark.e2e
async def test_record_set_without_active_workout(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест попытки записать подход без активной тренировки."""
    # Создаём зарегистрированного пользователя
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
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
    
