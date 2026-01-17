"""Integration тесты для SetEntryRepository."""
import pytest
from src.domain.models import (
    SetEntry,
    WorkoutSession,
    Machine,
    User,
    MuscleZone,
    Muscle,
    SetEntryZone,
    SetEntryMuscle,
)


@pytest.mark.integration
async def test_create_and_get_set_entry(
    set_entry_repository, workout_session_repository, machine_repository, test_user_data, test_session
):
    """Тест создания и получения подхода."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Создаём тренажёр
    machine = Machine(name="Test Machine", user_id=test_user_data["id"])
    await machine_repository.add(machine)
    await test_session.commit()
    
    # Создаём тренировку
    workout = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Создаём подход
    set_entry = SetEntry(
        session_id=workout.id,
        machine_id=machine.id,
        weight=100.0,
        reps=10,
        rir=2,
    )
    created_entry = await set_entry_repository.add(set_entry)
    await test_session.commit()
    
    # Проверяем
    assert created_entry.id is not None
    assert created_entry.session_id == workout.id
    assert created_entry.machine_id == machine.id
    assert created_entry.weight == 100.0
    assert created_entry.reps == 10
    assert created_entry.rir == 2
    
    # Получаем по ID
    retrieved_entry = await set_entry_repository.get_by_id(created_entry.id)
    assert retrieved_entry is not None
    assert retrieved_entry.weight == 100.0
    assert retrieved_entry.reps == 10


@pytest.mark.integration
async def test_update_set_entry(
    set_entry_repository, workout_session_repository, machine_repository, test_user_data, test_session
):
    """Тест обновления подхода."""
    # Создаём пользователя, тренажёр и тренировку
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    machine = Machine(name="Test Machine", user_id=test_user_data["id"])
    await machine_repository.add(machine)
    await test_session.commit()
    
    workout = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Создаём подход
    set_entry = SetEntry(
        session_id=workout.id,
        machine_id=machine.id,
        weight=100.0,
        reps=10,
        rir=2,
    )
    await set_entry_repository.add(set_entry)
    await test_session.commit()
    
    # Обновляем
    set_entry.weight = 120.0
    set_entry.reps = 8
    set_entry.rir = 0
    updated_entry = await set_entry_repository.update(set_entry)
    await test_session.commit()
    
    # Проверяем
    assert updated_entry.weight == 120.0
    assert updated_entry.reps == 8
    assert updated_entry.rir == 0
    
    # Проверяем в БД
    retrieved_entry = await set_entry_repository.get_by_id(set_entry.id)
    assert retrieved_entry.weight == 120.0
    assert retrieved_entry.reps == 8
    assert retrieved_entry.rir == 0


@pytest.mark.integration
async def test_delete_set_entry(
    set_entry_repository, workout_session_repository, machine_repository, test_user_data, test_session
):
    """Тест удаления подхода."""
    # Создаём пользователя, тренажёр и тренировку
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    machine = Machine(name="Test Machine", user_id=test_user_data["id"])
    await machine_repository.add(machine)
    await test_session.commit()
    
    workout = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Создаём подход
    set_entry = SetEntry(
        session_id=workout.id,
        machine_id=machine.id,
        weight=100.0,
        reps=10,
    )
    await set_entry_repository.add(set_entry)
    await test_session.commit()
    
    entry_id = set_entry.id
    
    # Проверяем, что подход существует
    assert await set_entry_repository.get_by_id(entry_id) is not None
    
    # Удаляем
    await set_entry_repository.delete(entry_id)
    await test_session.commit()
    
    # Проверяем, что подход удалён
    deleted_entry = await set_entry_repository.get_by_id(entry_id)
    assert deleted_entry is None


@pytest.mark.integration
async def test_add_set_entry_method(
    set_entry_repository, workout_session_repository, machine_repository, test_user_data, test_session
):
    """Тест метода add_set_entry (синоним add)."""
    # Создаём пользователя, тренажёр и тренировку
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    machine = Machine(name="Test Machine", user_id=test_user_data["id"])
    await machine_repository.add(machine)
    await test_session.commit()
    
    workout = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Создаём подход через add_set_entry
    set_entry = SetEntry(
        session_id=workout.id,
        machine_id=machine.id,
        weight=100.0,
        reps=10,
    )
    created_entry = await set_entry_repository.add_set_entry(set_entry)
    await test_session.commit()
    
    # Проверяем
    assert created_entry.id is not None
    assert created_entry.weight == 100.0
    assert created_entry.reps == 10


@pytest.mark.integration
async def test_multiple_set_entries_for_session(
    set_entry_repository, workout_session_repository, machine_repository, test_user_data, test_session
):
    """Тест создания нескольких подходов для одной тренировки."""
    # Создаём пользователя, тренажёр и тренировку
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    machine = Machine(name="Test Machine", user_id=test_user_data["id"])
    await machine_repository.add(machine)
    await test_session.commit()
    
    workout = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Создаём несколько подходов
    entry1 = SetEntry(
        session_id=workout.id,
        machine_id=machine.id,
        weight=100.0,
        reps=10,
    )
    entry2 = SetEntry(
        session_id=workout.id,
        machine_id=machine.id,
        weight=110.0,
        reps=8,
    )
    entry3 = SetEntry(
        session_id=workout.id,
        machine_id=machine.id,
        weight=120.0,
        reps=6,
    )
    
    await set_entry_repository.add(entry1)
    await set_entry_repository.add(entry2)
    await set_entry_repository.add(entry3)
    await test_session.commit()
    
    # Проверяем, что все подходы созданы
    assert entry1.id is not None
    assert entry2.id is not None
    assert entry3.id is not None
    
    # Проверяем, что все подходы принадлежат одной тренировке
    retrieved1 = await set_entry_repository.get_by_id(entry1.id)
    retrieved2 = await set_entry_repository.get_by_id(entry2.id)
    retrieved3 = await set_entry_repository.get_by_id(entry3.id)
    
    assert retrieved1.session_id == workout.id
    assert retrieved2.session_id == workout.id
    assert retrieved3.session_id == workout.id


@pytest.mark.integration
async def test_set_entry_with_failure(
    set_entry_repository, workout_session_repository, machine_repository, test_user_data, test_session
):
    """Тест создания подхода с rir=0."""
    # Создаём пользователя, тренажёр и тренировку
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    machine = Machine(name="Test Machine", user_id=test_user_data["id"])
    await machine_repository.add(machine)
    await test_session.commit()
    
    workout = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()
    
    # Создаём подход с rir
    set_entry = SetEntry(
        session_id=workout.id,
        machine_id=machine.id,
        weight=100.0,
        reps=10,
        rir=0,
    )
    created_entry = await set_entry_repository.add(set_entry)
    await test_session.commit()
    
    # Проверяем
    assert created_entry.rir == 0
    
    # Проверяем в БД
    retrieved_entry = await set_entry_repository.get_by_id(created_entry.id)
    assert retrieved_entry.rir == 0


@pytest.mark.integration
async def test_get_nonexistent_set_entry(set_entry_repository):
    """Тест получения несуществующего подхода."""
    entry = await set_entry_repository.get_by_id(999999)
    assert entry is None


@pytest.mark.integration
async def test_add_set_entry_snapshots(
    set_entry_repository, workout_session_repository, machine_repository, muscle_repository, test_user_data, test_session
):
    """Тест создания snapshot для подхода."""
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()

    zone = MuscleZone(name="Test Zone")
    muscle = Muscle(name="Test Muscle")
    await muscle_repository.add_muscle_zone(zone)
    await muscle_repository.add(muscle)
    await test_session.commit()

    machine = Machine(name="Test Machine", user_id=test_user_data["id"])
    await machine_repository.add(machine)
    await test_session.commit()

    workout = await workout_session_repository.start_session(test_user_data["id"])
    await test_session.commit()

    set_entry = SetEntry(
        session_id=workout.id,
        machine_id=machine.id,
        weight=100.0,
        reps=10,
        rir=2,
    )
    created_entry = await set_entry_repository.add(set_entry)
    await test_session.commit()

    await set_entry_repository.add_set_entry_snapshots(
        created_entry.id, [zone.id], [muscle.id]
    )
    await test_session.commit()

    zones = await test_session.get(SetEntryZone, (created_entry.id, zone.id))
    muscles = await test_session.get(SetEntryMuscle, (created_entry.id, muscle.id))
    assert zones is not None
    assert muscles is not None
