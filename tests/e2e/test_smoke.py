"""Smoke тесты основных функций бота."""
import pytest
from unittest.mock import AsyncMock
from src.domain.models import User, Machine, SetEntry
from src.infrastructure.web.handlers import registration

from tests.e2e.conftest import create_message_update, create_callback_query_update


@pytest.mark.e2e
@pytest.mark.slow
async def test_smoke_full_user_journey(
    bot, dispatcher, container, test_session, test_user_id, admin_user_id
):
    """Smoke тест полного пути пользователя: регистрация -> тренировка -> запись подходов."""
    # 1. Новый пользователь отправляет /start
    update1 = create_message_update("/start", user_id=test_user_id)
    bot.send_message = AsyncMock()
    await dispatcher.feed_update(bot, update1)
    
    # 2. Пользователь нажимает "Зарегистрироваться"
    callback1 = create_callback_query_update("register_request", user_id=test_user_id)
    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    await dispatcher.feed_update(bot, callback1)
    
    # 3. Пользователь отправляет описание
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey
    storage = dispatcher.storage
    key = StorageKey(bot_id=bot.id or 0, chat_id=test_user_id, user_id=test_user_id)
    state = FSMContext(storage=storage, key=key)
    await state.set_state(registration.RegistrationStates.waiting_for_description)
    
    update2 = create_message_update("Я хочу использовать бота", user_id=test_user_id)
    bot.send_message = AsyncMock()
    await dispatcher.feed_update(bot, update2)
    
    # Проверяем, что пользователь создан
    user = await container.user_repository().get_by_telegram_id(test_user_id)
    assert user is not None
    assert user.is_registered is False
    
    # 4. Администратор одобряет регистрацию
    callback2 = create_callback_query_update(
        f"admin_approve_{test_user_id}",
        user_id=admin_user_id,
    )
    bot.edit_message_text = AsyncMock()
    bot.send_message = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    await dispatcher.feed_update(bot, callback2)
    
    # Проверяем, что пользователь одобрен
    approved_user = await container.user_repository().get_by_id(test_user_id)
    assert approved_user is not None
    assert approved_user.is_registered is True

    machine = Machine(name="Test Machine", user_id=test_user_id)
    await container.machine_repository().add(machine)
    await test_session.commit()
    
    # 5. Пользователь начинает тренировку
    update3 = create_message_update("/workout_start", user_id=test_user_id)
    bot.send_message = AsyncMock()
    await dispatcher.feed_update(bot, update3)
    
    # Проверяем, что тренировка начата
    workout_repo = container.workout_session_repository()
    active_session = await workout_repo.get_active_session_for_user(test_user_id)
    assert active_session is not None
    session_id = active_session.id

    set_entry = SetEntry(
        session_id=session_id,
        machine_id=machine.id,
        weight=50,
        reps=10,
        is_failure=False,
    )
    await container.set_entry_repository().add(set_entry)
    await test_session.commit()
    
    # 6. Пользователь завершает тренировку
    update4 = create_message_update("/workout_end", user_id=test_user_id)
    bot.send_message = AsyncMock()
    await dispatcher.feed_update(bot, update4)
    
    # Проверяем, что тренировка завершена
    finished_session = await workout_repo.get_by_id(session_id)
    assert finished_session is not None
    assert finished_session.ended_at is not None


@pytest.mark.e2e
async def test_smoke_menu_command(
    bot, dispatcher, container, test_session, test_user_id
):
    """Smoke тест команды /menu."""
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
    
    # Пользователь отправляет /menu
    update = create_message_update("/menu", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что бот отправил меню


@pytest.mark.e2e
async def test_smoke_machines_command(
    bot, dispatcher, container, test_session, test_user_id
):
    """Smoke тест команды /machines."""
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
    
    # Пользователь отправляет /machines
    update = create_message_update("/machines", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что бот отправил меню тренажёров


@pytest.mark.e2e
async def test_smoke_google_sheets_command(
    bot, dispatcher, container, test_session, test_user_id
):
    """Smoke тест команды /google_sheets."""
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
    
    # Пользователь отправляет /google_sheets
    update = create_message_update("/google_sheets", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что бот отправил меню Google Sheets
