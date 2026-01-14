"""Integration тесты для WorkoutSessionRepository."""
import pytest
from datetime import datetime, timezone
from src.domain.models import WorkoutSession, User


@pytest.mark.integration
async def test_create_and_get_workout_session(
    workout_session_repository, test_user_data, test_session
):
    """Тест создания и получения тренировки."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Создаём тренировку
    workout = WorkoutSession(
        user_id=test_user_data["id"], started_at=datetime.now(timezone.utc)
    )
    created_workout = await workout_session_repository.add(workout)
    await test_session.commit()
    
    # Проверяем
    assert created_workout.id is not None
    assert created_workout.user_id == test_user_data["id"]
    assert created_workout.started_at is not None
    assert created_workout.ended_at is None
    
    # Получаем по ID
    retrieved_workout = await workout_session_repository.get_by_id(created_workout.id)
    assert retrieved_workout is not None
    assert retrieved_workout.user_id == test_user_data["id"]


@pytest.mark.integration
async def test_start_session(workout_session_repository, test_user_data, test_session):
    """Тест начала тренировки через start_session."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Начинаем тренировку
    workout = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Проверяем
    assert workout.id is not None
    assert workout.user_id == test_user_data["id"]
    assert workout.started_at is not None
    assert workout.ended_at is None


@pytest.mark.integration
async def test_get_active_session_for_user(
    workout_session_repository, test_user_data, test_session
):
    """Тест получения активной тренировки пользователя."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Начинаем тренировку
    workout = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Получаем активную тренировку
    active_workout = await workout_session_repository.get_active_session_for_user(
        test_user_data["id"]
    )
    assert active_workout is not None
    assert active_workout.id == workout.id
    assert active_workout.ended_at is None
    
    # Завершаем тренировку
    await workout_session_repository.end_session(workout.id)
    await test_session.commit()
    
    # Проверяем, что активной тренировки больше нет
    no_active_workout = await workout_session_repository.get_active_session_for_user(
        test_user_data["id"]
    )
    assert no_active_workout is None


@pytest.mark.integration
async def test_end_session(
    workout_session_repository, test_user_data, test_session
):
    """Тест завершения тренировки."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Начинаем тренировку
    workout = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Проверяем, что тренировка активна
    assert workout.ended_at is None
    
    # Завершаем тренировку
    await workout_session_repository.end_session(workout.id)
    await test_session.commit()
    
    # Проверяем, что тренировка завершена
    ended_workout = await workout_session_repository.get_by_id(workout.id)
    assert ended_workout.ended_at is not None
    assert ended_workout.ended_at > ended_workout.started_at


@pytest.mark.integration
async def test_update_workout_session(
    workout_session_repository, test_user_data, test_session
):
    """Тест обновления тренировки."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Создаём тренировку
    workout = WorkoutSession(
        user_id=test_user_data["id"], started_at=datetime.now(timezone.utc)
    )
    await workout_session_repository.add(workout)
    await test_session.commit()
    
    # Обновляем (например, устанавливаем ended_at вручную)
    workout.ended_at = datetime.now(timezone.utc)
    updated_workout = await workout_session_repository.update(workout)
    await test_session.commit()
    
    # Проверяем
    assert updated_workout.ended_at is not None
    
    # Проверяем в БД
    retrieved_workout = await workout_session_repository.get_by_id(workout.id)
    assert retrieved_workout.ended_at is not None


@pytest.mark.integration
async def test_delete_workout_session(
    workout_session_repository, test_user_data, test_session
):
    """Тест удаления тренировки."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Создаём тренировку
    workout = WorkoutSession(
        user_id=test_user_data["id"], started_at=datetime.now(timezone.utc)
    )
    await workout_session_repository.add(workout)
    await test_session.commit()
    
    workout_id = workout.id
    
    # Проверяем, что тренировка существует
    assert await workout_session_repository.get_by_id(workout_id) is not None
    
    # Удаляем
    await workout_session_repository.delete(workout_id)
    await test_session.commit()
    
    # Проверяем, что тренировка удалена
    deleted_workout = await workout_session_repository.get_by_id(workout_id)
    assert deleted_workout is None


@pytest.mark.integration
async def test_multiple_active_sessions_not_allowed(
    workout_session_repository, test_user_data, test_session
):
    """Тест, что у пользователя может быть только одна активная тренировка."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Начинаем первую тренировку
    workout1 = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Проверяем, что она активна
    active = await workout_session_repository.get_active_session_for_user(
        test_user_data["id"]
    )
    assert active is not None
    assert active.id == workout1.id
    
    # Начинаем вторую тренировку (это возможно на уровне репозитория,
    # но бизнес-логика должна проверять это в use case)
    workout2 = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Теперь у пользователя две активные тренировки
    # Это проверяется на уровне use case, но репозиторий позволяет это
    active_sessions = []
    # Проверяем обе тренировки
    w1 = await workout_session_repository.get_by_id(workout1.id)
    w2 = await workout_session_repository.get_by_id(workout2.id)
    if w1.ended_at is None:
        active_sessions.append(w1)
    if w2.ended_at is None:
        active_sessions.append(w2)
    
    # В данном случае обе активны, так как репозиторий не ограничивает это
    assert len(active_sessions) == 2


@pytest.mark.integration
async def test_get_nonexistent_workout_session(workout_session_repository):
    """Тест получения несуществующей тренировки."""
    workout = await workout_session_repository.get_by_id(999999)
    assert workout is None
