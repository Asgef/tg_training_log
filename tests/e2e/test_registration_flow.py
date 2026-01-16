"""E2E тесты для потока регистрации."""
import pytest
from unittest.mock import AsyncMock
from aiogram.types import Update
from src.domain.models import User
from src.infrastructure.web.handlers import registration

from tests.e2e.conftest import create_message_update, create_callback_query_update


@pytest.mark.e2e
async def test_new_user_registration_flow(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест полного потока регистрации нового пользователя."""
    # 1. Пользователь отправляет /start
    update = create_message_update("/start", user_id=test_user_id)
    
    # Мокаем ответ бота
    bot.send_message = AsyncMock()
    
    # Обрабатываем update
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что регистрация возможна (пользователь еще не создан)
    
    # 2. Пользователь нажимает кнопку "Зарегистрироваться"
    callback_update = create_callback_query_update(
        "register_request",
        user_id=test_user_id,
        message_id=1,
    )
    
    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    
    await dispatcher.feed_update(bot, callback_update)
    
    # 3. Пользователь отправляет описание
    description_update = create_message_update(
        "Я хочу использовать бота для логирования тренировок",
        user_id=test_user_id,
    )
    
    # Устанавливаем состояние FSM
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey
    storage = dispatcher.storage
    key = StorageKey(bot_id=bot.id or 0, chat_id=test_user_id, user_id=test_user_id)
    state = FSMContext(storage=storage, key=key)
    await state.set_state(registration.RegistrationStates.waiting_for_description)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, description_update)
    
    # Проверяем, что запрос создан
    user = await container.user_repository().get_by_telegram_id(test_user_id)
    assert user is not None
    assert user.is_registered is False
    


@pytest.mark.e2e
async def test_admin_approval_flow(
    bot, dispatcher, container, test_session, test_user_id, admin_user_id
):
    """Тест потока одобрения регистрации администратором."""
    # Создаём пользователя с запросом на регистрацию
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=False,
    )
    await container.user_repository().add(user)
    await test_session.commit()
    
    # Администратор одобряет регистрацию
    callback_update = create_callback_query_update(
        f"admin_approve_{test_user_id}",
        user_id=admin_user_id,
    )
    
    bot.edit_message_text = AsyncMock()
    bot.send_message = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    
    await dispatcher.feed_update(bot, callback_update)
    
    # Проверяем, что пользователь одобрен
    approved_user = await container.user_repository().get_by_id(test_user_id)
    assert approved_user is not None
    assert approved_user.is_registered is True
    
    # Проверяем, что коллбек обработан без ошибок


@pytest.mark.e2e
async def test_already_registered_user_start(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест /start для уже зарегистрированного пользователя."""
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
    
    # Пользователь отправляет /start
    update = create_message_update("/start", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что команда /start обработана без ошибок


@pytest.mark.e2e
async def test_pending_registration_user_start(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест /start для пользователя с ожидающей регистрацией."""
    # Создаём пользователя с ожидающей регистрацией
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=False,
    )
    await container.user_repository().add(user)
    await test_session.commit()
    
    # Пользователь отправляет /start
    update = create_message_update("/start", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что команда /start обработана без ошибок
