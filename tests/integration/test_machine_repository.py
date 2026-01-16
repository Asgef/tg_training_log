"""Integration тесты для MachineRepository."""
import pytest
from src.domain.models import Machine, User, Muscle, MuscleZone


@pytest.mark.integration
async def test_create_and_get_machine(machine_repository, test_user_data, test_session):
    """Тест создания и получения тренажёра."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Создаём тренажёр
    machine = Machine(name="Test Machine", user_id=test_user_data["id"])
    created_machine = await machine_repository.add(machine)
    await test_session.commit()
    
    # Проверяем
    assert created_machine.id is not None
    assert created_machine.name == "Test Machine"
    assert created_machine.user_id == test_user_data["id"]
    
    # Получаем по ID
    retrieved_machine = await machine_repository.get_by_id(created_machine.id)
    assert retrieved_machine is not None
    assert retrieved_machine.name == "Test Machine"
    assert retrieved_machine.user_id == test_user_data["id"]


@pytest.mark.integration
async def test_update_machine(machine_repository, test_user_data, test_session):
    """Тест обновления тренажёра."""
    # Создаём пользователя и тренажёр
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    machine = Machine(name="Original Name", user_id=test_user_data["id"])
    await machine_repository.add(machine)
    await test_session.commit()
    
    # Обновляем
    machine.name = "Updated Name"
    machine.is_archived = True
    updated_machine = await machine_repository.update(machine)
    await test_session.commit()
    
    # Проверяем
    assert updated_machine.name == "Updated Name"
    assert updated_machine.is_archived is True
    
    # Проверяем в БД
    retrieved_machine = await machine_repository.get_by_id(machine.id)
    assert retrieved_machine.name == "Updated Name"
    assert retrieved_machine.is_archived is True


@pytest.mark.integration
async def test_delete_machine(machine_repository, test_user_data, test_session):
    """Тест удаления тренажёра."""
    # Создаём пользователя и тренажёр
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    machine = Machine(name="To Delete", user_id=test_user_data["id"])
    await machine_repository.add(machine)
    await test_session.commit()
    
    machine_id = machine.id
    
    # Проверяем, что тренажёр существует
    assert await machine_repository.get_by_id(machine_id) is not None
    
    # Удаляем
    await machine_repository.delete(machine_id)
    await test_session.commit()
    
    # Проверяем, что тренажёр удалён
    deleted_machine = await machine_repository.get_by_id(machine_id)
    assert deleted_machine is None


@pytest.mark.integration
async def test_get_user_machines(machine_repository, test_user_data, test_session):
    """Тест получения тренажёров пользователя."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Создаём несколько тренажёров
    machine1 = Machine(name="Machine 1", user_id=test_user_data["id"], is_archived=False)
    machine2 = Machine(name="Machine 2", user_id=test_user_data["id"], is_archived=False)
    machine3 = Machine(name="Machine 3", user_id=test_user_data["id"], is_archived=True)
    
    await machine_repository.add(machine1)
    await machine_repository.add(machine2)
    await machine_repository.add(machine3)
    await test_session.commit()
    
    # Получаем активные тренажёры
    active_machines = await machine_repository.get_user_machines(
        test_user_data["id"], include_archived=False
    )
    assert len(active_machines) == 2
    
    # Получаем все тренажёры включая архивные
    all_machines = await machine_repository.get_user_machines(
        test_user_data["id"], include_archived=True
    )
    assert len(all_machines) == 3


@pytest.mark.integration
async def test_get_user_machine_by_name(machine_repository, test_user_data, test_session):
    """Тест получения тренажёра по имени."""
    # Создаём пользователя и тренажёр
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    machine = Machine(name="Unique Machine", user_id=test_user_data["id"])
    await machine_repository.add(machine)
    await test_session.commit()
    
    # Получаем по имени
    retrieved_machine = await machine_repository.get_user_machine_by_name(
        test_user_data["id"], "Unique Machine"
    )
    assert retrieved_machine is not None
    assert retrieved_machine.name == "Unique Machine"
    
    # Проверяем несуществующий тренажёр
    nonexistent = await machine_repository.get_user_machine_by_name(
        test_user_data["id"], "Nonexistent"
    )
    assert nonexistent is None


@pytest.mark.integration
async def test_add_machine_with_muscles(
    machine_repository, muscle_repository, test_user_data, test_session
):
    """Тест создания тренажёра с мышцами."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Создаём зону и мышцы
    zone = MuscleZone(name="Test Zone")
    await muscle_repository.add_muscle_zone(zone)
    await test_session.commit()
    
    muscle1 = Muscle(name="Muscle 1")
    muscle2 = Muscle(name="Muscle 2")
    await muscle_repository.add(muscle1)
    await muscle_repository.add(muscle2)
    await test_session.commit()
    
    # Создаём тренажёр с зонами и мышцами
    machine = Machine(name="Machine with Muscles", user_id=test_user_data["id"])
    created_machine = await machine_repository.add_machine_with_tags(
        machine, [zone.id], [muscle1.id, muscle2.id]
    )
    await test_session.commit()
    
    # Проверяем
    assert created_machine.id is not None
    retrieved_machine = await machine_repository.get_by_id(created_machine.id)
    assert retrieved_machine is not None
    assert len(retrieved_machine.zones) == 1
    assert len(retrieved_machine.muscles) == 2
    muscle_ids = {m.id for m in retrieved_machine.muscles}
    assert muscle1.id in muscle_ids
    assert muscle2.id in muscle_ids


@pytest.mark.integration
async def test_update_machine_muscles(
    machine_repository, muscle_repository, test_user_data, test_session
):
    """Тест обновления мышц тренажёра."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()
    
    # Создаём зону и мышцы
    zone = MuscleZone(name="Test Zone")
    await muscle_repository.add_muscle_zone(zone)
    await test_session.commit()
    
    muscle1 = Muscle(name="Muscle 1")
    muscle2 = Muscle(name="Muscle 2")
    muscle3 = Muscle(name="Muscle 3")
    await muscle_repository.add(muscle1)
    await muscle_repository.add(muscle2)
    await muscle_repository.add(muscle3)
    await test_session.commit()
    
    # Создаём тренажёр с начальными зонами и мышцами
    machine = Machine(name="Machine", user_id=test_user_data["id"])
    await machine_repository.add_machine_with_tags(
        machine, [zone.id], [muscle1.id, muscle2.id]
    )
    await test_session.commit()
    
    # Проверяем начальное состояние
    retrieved_machine = await machine_repository.get_by_id(machine.id)
    assert len(retrieved_machine.muscles) == 2
    
    # Обновляем мышцы
    await machine_repository.update_machine_muscles(machine.id, [muscle2.id, muscle3.id])
    await test_session.commit()
    
    # Проверяем обновлённое состояние
    updated_machine = await machine_repository.get_by_id(machine.id)
    assert len(updated_machine.muscles) == 2
    muscle_ids = {m.id for m in updated_machine.muscles}
    assert muscle1.id not in muscle_ids
    assert muscle2.id in muscle_ids
    assert muscle3.id in muscle_ids


@pytest.mark.integration
async def test_update_machine_zones(
    machine_repository, muscle_repository, test_user_data, test_session
):
    """Тест обновления зон тренажёра."""
    # Создаём пользователя
    user = User(**test_user_data)
    test_session.add(user)
    await test_session.commit()

    zone1 = MuscleZone(name="Zone 1")
    zone2 = MuscleZone(name="Zone 2")
    zone3 = MuscleZone(name="Zone 3")
    await muscle_repository.add_muscle_zone(zone1)
    await muscle_repository.add_muscle_zone(zone2)
    await muscle_repository.add_muscle_zone(zone3)
    await test_session.commit()

    machine = Machine(name="Machine", user_id=test_user_data["id"])
    await machine_repository.add_machine_with_tags(machine, [zone1.id, zone2.id], [])
    await test_session.commit()

    retrieved_machine = await machine_repository.get_by_id(machine.id)
    assert len(retrieved_machine.zones) == 2

    await machine_repository.update_machine_zones(machine.id, [zone2.id, zone3.id])
    await test_session.commit()

    updated_machine = await machine_repository.get_by_id(machine.id)
    zone_ids = {z.id for z in updated_machine.zones}
    assert zone1.id not in zone_ids
    assert zone2.id in zone_ids
    assert zone3.id in zone_ids


@pytest.mark.integration
async def test_get_nonexistent_machine(machine_repository):
    """Тест получения несуществующего тренажёра."""
    machine = await machine_repository.get_by_id(999999)
    assert machine is None
