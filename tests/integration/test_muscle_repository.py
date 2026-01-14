"""Integration тесты для MuscleRepository."""
import pytest
from src.domain.models import Muscle, MuscleGroup


@pytest.mark.integration
async def test_create_and_get_muscle(muscle_repository, test_session):
    """Тест создания и получения мышцы."""
    # Создаём группу мышц
    group = MuscleGroup(name="Test Group")
    await muscle_repository.add_muscle_group(group)
    await test_session.commit()
    
    # Создаём мышцу
    muscle = Muscle(name="Test Muscle", group_id=group.id)
    created_muscle = await muscle_repository.add(muscle)
    await test_session.commit()
    
    # Проверяем
    assert created_muscle.id is not None
    assert created_muscle.name == "Test Muscle"
    assert created_muscle.group_id == group.id
    
    # Получаем по ID
    retrieved_muscle = await muscle_repository.get_by_id(created_muscle.id)
    assert retrieved_muscle is not None
    assert retrieved_muscle.name == "Test Muscle"
    assert retrieved_muscle.group_id == group.id


@pytest.mark.integration
async def test_update_muscle(muscle_repository, test_session):
    """Тест обновления мышцы."""
    # Создаём группу мышц и мышцу
    group = MuscleGroup(name="Test Group")
    await muscle_repository.add_muscle_group(group)
    await test_session.commit()
    
    muscle = Muscle(name="Original Name", group_id=group.id)
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
    # Создаём группу мышц и мышцу
    group = MuscleGroup(name="Test Group")
    await muscle_repository.add_muscle_group(group)
    await test_session.commit()
    
    muscle = Muscle(name="To Delete", group_id=group.id)
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
    # Создаём группу мышц
    group = MuscleGroup(name="Test Group")
    await muscle_repository.add_muscle_group(group)
    await test_session.commit()
    
    # Создаём несколько мышц
    muscle1 = Muscle(name="Muscle 1", group_id=group.id)
    muscle2 = Muscle(name="Muscle 2", group_id=group.id)
    muscle3 = Muscle(name="Muscle 3", group_id=group.id)
    
    await muscle_repository.add(muscle1)
    await muscle_repository.add(muscle2)
    await muscle_repository.add(muscle3)
    await test_session.commit()
    
    # Получаем все мышцы
    all_muscles = await muscle_repository.get_all_muscles()
    
    # Проверяем, что все мышцы получены (может быть больше из других тестов)
    muscle_ids = {m.id for m in all_muscles}
    assert muscle1.id in muscle_ids
    assert muscle2.id in muscle_ids
    assert muscle3.id in muscle_ids
    
    # Проверяем, что загружены группы
    for muscle in all_muscles:
        if muscle.id in (muscle1.id, muscle2.id, muscle3.id):
            assert muscle.group is not None
            assert muscle.group.id == group.id


@pytest.mark.integration
async def test_get_muscles_by_ids(muscle_repository, test_session):
    """Тест получения мышц по списку ID."""
    # Создаём группу мышц
    group = MuscleGroup(name="Test Group")
    await muscle_repository.add_muscle_group(group)
    await test_session.commit()
    
    # Создаём несколько мышц
    muscle1 = Muscle(name="Muscle 1", group_id=group.id)
    muscle2 = Muscle(name="Muscle 2", group_id=group.id)
    muscle3 = Muscle(name="Muscle 3", group_id=group.id)
    
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
async def test_get_muscles_by_group_id(muscle_repository, test_session):
    """Тест получения мышц по ID группы."""
    # Создаём две группы мышц
    group1 = MuscleGroup(name="Group 1")
    group2 = MuscleGroup(name="Group 2")
    await muscle_repository.add_muscle_group(group1)
    await muscle_repository.add_muscle_group(group2)
    await test_session.commit()
    
    # Создаём мышцы в разных группах
    muscle1 = Muscle(name="Muscle 1", group_id=group1.id)
    muscle2 = Muscle(name="Muscle 2", group_id=group1.id)
    muscle3 = Muscle(name="Muscle 3", group_id=group2.id)
    
    await muscle_repository.add(muscle1)
    await muscle_repository.add(muscle2)
    await muscle_repository.add(muscle3)
    await test_session.commit()
    
    # Получаем мышцы первой группы
    group1_muscles = await muscle_repository.get_muscles_by_group_id(group1.id)
    
    # Проверяем
    assert len(group1_muscles) == 2
    muscle_ids = {m.id for m in group1_muscles}
    assert muscle1.id in muscle_ids
    assert muscle2.id in muscle_ids
    assert muscle3.id not in muscle_ids


@pytest.mark.integration
async def test_get_all_muscle_groups(muscle_repository, test_session):
    """Тест получения всех групп мышц."""
    # Создаём несколько групп
    group1 = MuscleGroup(name="Group 1")
    group2 = MuscleGroup(name="Group 2")
    group3 = MuscleGroup(name="Group 3")
    
    await muscle_repository.add_muscle_group(group1)
    await muscle_repository.add_muscle_group(group2)
    await muscle_repository.add_muscle_group(group3)
    await test_session.commit()
    
    # Получаем все группы
    all_groups = await muscle_repository.get_all_muscle_groups()
    
    # Проверяем, что все группы получены (может быть больше из других тестов)
    group_ids = {g.id for g in all_groups}
    assert group1.id in group_ids
    assert group2.id in group_ids
    assert group3.id in group_ids


@pytest.mark.integration
async def test_get_muscle_group_by_id(muscle_repository, test_session):
    """Тест получения группы мышц по ID."""
    # Создаём группу
    group = MuscleGroup(name="Test Group")
    await muscle_repository.add_muscle_group(group)
    await test_session.commit()
    
    # Получаем по ID
    retrieved_group = await muscle_repository.get_muscle_group_by_id(group.id)
    assert retrieved_group is not None
    assert retrieved_group.name == "Test Group"
    
    # Проверяем несуществующую группу
    nonexistent = await muscle_repository.get_muscle_group_by_id(999999)
    assert nonexistent is None


@pytest.mark.integration
async def test_add_muscle_group(muscle_repository, test_session):
    """Тест создания группы мышц."""
    group = MuscleGroup(name="New Group")
    created_group = await muscle_repository.add_muscle_group(group)
    await test_session.commit()
    
    # Проверяем
    assert created_group.id is not None
    assert created_group.name == "New Group"
    
    # Проверяем в БД
    retrieved_group = await muscle_repository.get_muscle_group_by_id(created_group.id)
    assert retrieved_group is not None
    assert retrieved_group.name == "New Group"


@pytest.mark.integration
async def test_get_nonexistent_muscle(muscle_repository):
    """Тест получения несуществующей мышцы."""
    muscle = await muscle_repository.get_by_id(999999)
    assert muscle is None
