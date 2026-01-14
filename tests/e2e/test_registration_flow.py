"""E2E тесты для потока регистрации."""
import pytest
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
    
    # Проверяем, что бот отправил сообщение с кнопкой регистрации
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "зарегистрироваться" in call_args.kwargs["text"].lower() or "register" in call_args.kwargs["text"].lower()
    
    # 2. Пользователь нажимает кнопку "Зарегистрироваться"
    callback_update = create_callback_query_update(
        "register_request",
        user_id=test_user_id,
        message_id=1,
    )
    
    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    
    await dispatcher.feed_update(bot, callback_update)
    
    # Проверяем, что бот запросил описание
    assert bot.edit_message_text.called
    assert "расскажите" in bot.edit_message_text.call_args.kwargs["text"].lower() or "описание" in bot.edit_message_text.call_args.kwargs["text"].lower()
    
    # 3. Пользователь отправляет описание
    description_update = create_message_update(
        "Я хочу использовать бота для логирования тренировок",
        user_id=test_user_id,
    )
    
    # Устанавливаем состояние FSM
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.memory import MemoryStorage
    storage = dispatcher.storage
    state = FSMContext(storage=storage, key=storage.resolve_key(bot, test_user_id, test_user_id))
    await state.set_state(registration.RegistrationStates.waiting_for_description)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, description_update)
    
    # Проверяем, что запрос создан
    user = await container.user_repository().get_by_telegram_id(test_user_id)
    assert user is not None
    assert user.is_registered is False
    
    # Проверяем, что пользователю отправлено сообщение об ожидании одобрения
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "одобрения" in call_args.kwargs["text"].lower() or "ожидает" in call_args.kwargs["text"].lower()


@pytest.mark.e2e
async def test_admin_approval_flow(
    bot, dispatcher, container, test_session, test_user_id, admin_user_id
):
    """Тест потока одобрения регистрации администратором."""
    # Создаём пользователя с запросом на регистрацию
    user = User(
        id=test_user_id,
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
    await test_session.refresh(user)
    assert user.is_registered is True
    
    # Проверяем, что администратор получил подтверждение
    assert bot.edit_message_text.called
    assert "одобрен" in bot.edit_message_text.call_args.kwargs["text"].lower()
    
    # Проверяем, что пользователь получил уведомление
    assert bot.send_message.called
    # Находим вызов для пользователя
    user_notification = None
    for call in bot.send_message.call_args_list:
        if call.kwargs.get("chat_id") == test_user_id:
            user_notification = call
            break
    assert user_notification is not None
    assert "одобрена" in user_notification.kwargs["text"].lower()


@pytest.mark.e2e
async def test_already_registered_user_start(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест /start для уже зарегистрированного пользователя."""
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
    
    # Пользователь отправляет /start
    update = create_message_update("/start", user_id=test_user_id)
    
    bot.send_message = AsyncMock()
    
    await dispatcher.feed_update(bot, update)
    
    # Проверяем, что бот отправил приветствие с главным меню
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "возвращением" in call_args.kwargs["text"].lower() or "зарегистрирован" in call_args.kwargs["text"].lower()
    assert "reply_markup" in call_args.kwargs


@pytest.mark.e2e
async def test_pending_registration_user_start(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест /start для пользователя с ожидающей регистрацией."""
    # Создаём пользователя с ожидающей регистрацией
    user = User(
        id=test_user_id,
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
    
    # Проверяем, что бот сообщил об ожидании одобрения
    assert bot.send_message.called
    call_args = bot.send_message.call_args
    assert "одобрения" in call_args.kwargs["text"].lower() or "ожидает" in call_args.kwargs["text"].lower()
