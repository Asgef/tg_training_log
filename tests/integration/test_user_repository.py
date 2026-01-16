"""Integration тесты для UserRepository."""
import pytest
from src.domain.models import User


@pytest.mark.integration
async def test_create_and_get_user(user_repository, test_user_data, test_session):
    """Тест создания и получения пользователя."""
    # Создаём пользователя
    user = User(**test_user_data)
    created_user = await user_repository.add(user)
    await test_session.commit()
    
    # Проверяем, что пользователь создан
    assert created_user.id == test_user_data["id"]
    assert created_user.telegram_username == test_user_data["telegram_username"]
    
    # Получаем пользователя по ID
    retrieved_user = await user_repository.get_by_id(test_user_data["id"])
    assert retrieved_user is not None
    assert retrieved_user.id == test_user_data["id"]
    assert retrieved_user.telegram_username == test_user_data["telegram_username"]


@pytest.mark.integration
async def test_get_user_by_telegram_id(user_repository, test_user_data, test_session):
    """Тест получения пользователя по telegram_id."""
    # Создаём пользователя
    user = User(**test_user_data)
    await user_repository.add(user)
    await test_session.commit()
    
    # Получаем по telegram_id
    retrieved_user = await user_repository.get_by_telegram_id(test_user_data["id"])
    assert retrieved_user is not None
    assert retrieved_user.id == test_user_data["id"]


@pytest.mark.integration
async def test_update_user(user_repository, test_user_data, test_session):
    """Тест обновления пользователя."""
    # Создаём пользователя
    user = User(**test_user_data)
    await user_repository.add(user)
    await test_session.commit()
    
    # Обновляем
    user.is_registered = True
    user.telegram_username = "updated_username"
    updated_user = await user_repository.update(user)
    await test_session.commit()
    
    # Проверяем
    assert updated_user.is_registered is True
    assert updated_user.telegram_username == "updated_username"
    
    # Проверяем в БД
    retrieved_user = await user_repository.get_by_id(test_user_data["id"])
    assert retrieved_user.is_registered is True
    assert retrieved_user.telegram_username == "updated_username"


@pytest.mark.integration
async def test_delete_user(user_repository, test_user_data, test_session):
    """Тест удаления пользователя."""
    # Создаём пользователя
    user = User(**test_user_data)
    await user_repository.add(user)
    await test_session.commit()
    
    # Проверяем, что пользователь существует
    assert await user_repository.get_by_id(test_user_data["id"]) is not None
    
    # Удаляем
    await user_repository.delete(test_user_data["id"])
    await test_session.commit()
    
    # Проверяем, что пользователь удалён
    deleted_user = await user_repository.get_by_id(test_user_data["id"])
    assert deleted_user is None


@pytest.mark.integration
async def test_get_nonexistent_user(user_repository):
    """Тест получения несуществующего пользователя."""
    user = await user_repository.get_by_id(999999999)
    assert user is None


@pytest.mark.integration
async def test_get_admin_approved_users(user_repository, test_session):
    """Тест получения одобренных администратором пользователей."""
    # Создаём несколько пользователей
    user1 = User(id=111, telegram_id=111, telegram_username="user1", is_registered=True)
    user2 = User(id=222, telegram_id=222, telegram_username="user2", is_registered=False)
    user3 = User(id=333, telegram_id=333, telegram_username="user3", is_registered=True)
    
    await user_repository.add(user1)
    await user_repository.add(user2)
    await user_repository.add(user3)
    await test_session.commit()
    
    # Получаем одобренных пользователей
    approved_users = await user_repository.get_admin_approved_users()
    
    # Проверяем
    assert len(approved_users) == 2
    user_ids = {u.id for u in approved_users}
    assert 111 in user_ids
    assert 333 in user_ids
    assert 222 not in user_ids


@pytest.mark.integration
async def test_save_google_sheet_config(user_repository, test_user_data, test_session):
    """Тест сохранения конфигурации Google Sheet."""
    # Создаём пользователя
    user = User(**test_user_data)
    await user_repository.add(user)
    await test_session.commit()
    
    # Сохраняем конфигурацию
    url = "https://docs.google.com/spreadsheets/d/test123"
    spreadsheet_id = "test123"
    await user_repository.save_google_sheet_config(test_user_data["id"], url, spreadsheet_id)
    await test_session.commit()
    
    # Проверяем
    retrieved_user = await user_repository.get_by_id(test_user_data["id"])
    assert retrieved_user.google_sheet_url == url
    assert retrieved_user.spreadsheet_id == spreadsheet_id
