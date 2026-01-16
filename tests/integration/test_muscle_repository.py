"""Integration тесты для MuscleRepository."""
import pytest
from sqlalchemy import select
from src.domain.models import Muscle, MuscleZone, MuscleZoneMuscle


@pytest.mark.integration
async def test_create_and_get_muscle(muscle_repository, test_session):
    """Тест создания и получения мышцы."""
    # Создаём зону
    zone = MuscleZone(name="Test Zone")
    await muscle_repository.add_muscle_zone(zone)
    await test_session.commit()
    
    # Создаём мышцу
    muscle = Muscle(name="Test Muscle")
    created_muscle = await muscle_repository.add(muscle)
    muscle_id = created_muscle.id
    await test_session.commit()

    # Связываем мышцу с зоной
    test_session.add(MuscleZoneMuscle(zone_id=zone.id, muscle_id=muscle_id))
    await test_session.commit()
    test_session.expire_all()
    
    # Проверяем
    assert muscle_id is not None
    
    # Получаем по ID
    retrieved_muscle = await muscle_repository.get_by_id(muscle_id)
    assert retrieved_muscle is not None
    assert retrieved_muscle.name == "Test Muscle"
    link = await test_session.get(MuscleZoneMuscle, (zone.id, muscle_id))
    assert link is not None


@pytest.mark.integration
async def test_update_muscle(muscle_repository, test_session):
    """Тест обновления мышцы."""
    # Создаём мышцу
    muscle = Muscle(name="Original Name")
    await muscle_repository.add(muscle)
    await test_session.commit()
    
    # Обновляем
    muscle.name = "Updated Name"
    updated_muscle = await muscle_repository.update(muscle)
    await test_session.commit()
    
    # Проверяем
    assert updated_muscle.name == "Updated Name"
    
    # Проверяем в БД
    retrieved_muscle = await muscle_repository.get_by_id(muscle.id)
    assert retrieved_muscle.name == "Updated Name"


@pytest.mark.integration
async def test_delete_muscle(muscle_repository, test_session):
    """Тест удаления мышцы."""
    # Создаём мышцу
    muscle = Muscle(name="To Delete")
    await muscle_repository.add(muscle)
    await test_session.commit()
    
    muscle_id = muscle.id
    
    # Проверяем, что мышца существует
    assert await muscle_repository.get_by_id(muscle_id) is not None
    
    # Удаляем
    await muscle_repository.delete(muscle_id)
    await test_session.commit()
    
    # Проверяем, что мышца удалена
    deleted_muscle = await muscle_repository.get_by_id(muscle_id)
    assert deleted_muscle is None


@pytest.mark.integration
async def test_get_all_muscles(muscle_repository, test_session):
    """Тест получения всех мышц."""
    # Создаём зону
    zone = MuscleZone(name="Test Zone")
    await muscle_repository.add_muscle_zone(zone)
    await test_session.commit()
    
    # Создаём несколько мышц
    muscle1 = Muscle(name="Muscle 1")
    muscle2 = Muscle(name="Muscle 2")
    muscle3 = Muscle(name="Muscle 3")
    
    await muscle_repository.add(muscle1)
    await muscle_repository.add(muscle2)
    await muscle_repository.add(muscle3)
    await test_session.commit()

    # Связываем мышцы с зоной
    test_session.add(MuscleZoneMuscle(zone_id=zone.id, muscle_id=muscle1.id))
    test_session.add(MuscleZoneMuscle(zone_id=zone.id, muscle_id=muscle2.id))
    test_session.add(MuscleZoneMuscle(zone_id=zone.id, muscle_id=muscle3.id))
    await test_session.commit()
    test_session.expire_all()
    
    # Получаем все мышцы
    all_muscles = await muscle_repository.get_all_muscles()
    
    # Проверяем, что все мышцы получены (может быть больше из других тестов)
    muscle_ids = {m.id for m in all_muscles}
    assert muscle1.id in muscle_ids
    assert muscle2.id in muscle_ids
    assert muscle3.id in muscle_ids
    
    # Проверяем, что есть связи с зонами
    for muscle_id in (muscle1.id, muscle2.id, muscle3.id):
        link = await test_session.execute(
            select(MuscleZoneMuscle).where(MuscleZoneMuscle.muscle_id == muscle_id)
        )
        assert link.scalar_one_or_none() is not None


@pytest.mark.integration
async def test_get_muscles_by_ids(muscle_repository, test_session):
    """Тест получения мышц по списку ID."""
    # Создаём несколько мышц
    muscle1 = Muscle(name="Muscle 1")
    muscle2 = Muscle(name="Muscle 2")
    muscle3 = Muscle(name="Muscle 3")
    
    await muscle_repository.add(muscle1)
    await muscle_repository.add(muscle2)
    await muscle_repository.add(muscle3)
    await test_session.commit()
    
    # Получаем мышцы по ID
    muscles = await muscle_repository.get_muscles_by_ids([muscle1.id, muscle3.id])
    
    # Проверяем
    assert len(muscles) == 2
    muscle_ids = {m.id for m in muscles}
    assert muscle1.id in muscle_ids
    assert muscle3.id in muscle_ids
    assert muscle2.id not in muscle_ids


@pytest.mark.integration
async def test_get_muscles_by_zone_id(muscle_repository, test_session):
    """Тест получения мышц по ID зоны."""
    # Создаём две зоны
    zone1 = MuscleZone(name="Zone 1")
    zone2 = MuscleZone(name="Zone 2")
    await muscle_repository.add_muscle_zone(zone1)
    await muscle_repository.add_muscle_zone(zone2)
    await test_session.commit()
    
    # Создаём мышцы
    muscle1 = Muscle(name="Muscle 1")
    muscle2 = Muscle(name="Muscle 2")
    muscle3 = Muscle(name="Muscle 3")
    
    await muscle_repository.add(muscle1)
    await muscle_repository.add(muscle2)
    await muscle_repository.add(muscle3)
    await test_session.commit()
    
    # Связываем мышцы с зонами
    test_session.add(MuscleZoneMuscle(zone_id=zone1.id, muscle_id=muscle1.id))
    test_session.add(MuscleZoneMuscle(zone_id=zone1.id, muscle_id=muscle2.id))
    test_session.add(MuscleZoneMuscle(zone_id=zone2.id, muscle_id=muscle3.id))
    await test_session.commit()
    
    # Получаем мышцы первой зоны
    zone1_muscles = await muscle_repository.get_muscles_by_zone_id(zone1.id)
    
    # Проверяем
    assert len(zone1_muscles) == 2
    muscle_ids = {m.id for m in zone1_muscles}
    assert muscle1.id in muscle_ids
    assert muscle2.id in muscle_ids
    assert muscle3.id not in muscle_ids


@pytest.mark.integration
async def test_get_all_muscle_zones(muscle_repository, test_session):
    """Тест получения всех зон."""
    # Создаём несколько зон
    zone1 = MuscleZone(name="Zone 1")
    zone2 = MuscleZone(name="Zone 2")
    zone3 = MuscleZone(name="Zone 3")
    
    await muscle_repository.add_muscle_zone(zone1)
    await muscle_repository.add_muscle_zone(zone2)
    await muscle_repository.add_muscle_zone(zone3)
    await test_session.commit()
    
    # Получаем все зоны
    all_zones = await muscle_repository.get_all_muscle_zones()
    
    # Проверяем, что все группы получены (может быть больше из других тестов)
    zone_ids = {z.id for z in all_zones}
    assert zone1.id in zone_ids
    assert zone2.id in zone_ids
    assert zone3.id in zone_ids


@pytest.mark.integration
async def test_get_muscle_zone_by_id(muscle_repository, test_session):
    """Тест получения зоны по ID."""
    # Создаём зону
    zone = MuscleZone(name="Test Zone")
    await muscle_repository.add_muscle_zone(zone)
    await test_session.commit()
    
    # Получаем по ID
    retrieved_zone = await muscle_repository.get_muscle_zone_by_id(zone.id)
    assert retrieved_zone is not None
    assert retrieved_zone.name == "Test Zone"
    
    # Проверяем несуществующую зону
    nonexistent = await muscle_repository.get_muscle_zone_by_id(999999)
    assert nonexistent is None


@pytest.mark.integration
async def test_add_muscle_zone(muscle_repository, test_session):
    """Тест создания зоны."""
    zone = MuscleZone(name="New Zone")
    created_zone = await muscle_repository.add_muscle_zone(zone)
    await test_session.commit()
    
    # Проверяем
    assert created_zone.id is not None
    assert created_zone.name == "New Zone"
    
    # Проверяем в БД
    retrieved_zone = await muscle_repository.get_muscle_zone_by_id(created_zone.id)
    assert retrieved_zone is not None
    assert retrieved_zone.name == "New Zone"


@pytest.mark.integration
async def test_get_nonexistent_muscle(muscle_repository):
    """Тест получения несуществующей мышцы."""
    muscle = await muscle_repository.get_by_id(999999)
    assert muscle is None
