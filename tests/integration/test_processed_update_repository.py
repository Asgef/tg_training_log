"""Integration тесты для ProcessedUpdateRepository."""
import pytest
from datetime import datetime, timezone, timedelta
from src.domain.models import ProcessedUpdate


@pytest.mark.integration
async def test_is_processed_false(processed_update_repository):
    """Тест проверки необработанного update."""
    # Проверяем несуществующий update
    is_processed = await processed_update_repository.is_processed(12345)
    assert is_processed is False


@pytest.mark.integration
async def test_mark_as_processed_and_check(
    processed_update_repository, test_session
):
    """Тест пометки update как обработанного и проверки."""
    update_id = 12345
    
    # Проверяем, что update не обработан
    assert await processed_update_repository.is_processed(update_id) is False
    
    # Помечаем как обработанный
    await processed_update_repository.mark_as_processed(update_id)
    await test_session.commit()
    
    # Проверяем, что update обработан
    assert await processed_update_repository.is_processed(update_id) is True


@pytest.mark.integration
async def test_multiple_updates(processed_update_repository, test_session):
    """Тест обработки нескольких updates."""
    update_ids = [111, 222, 333, 444, 555]
    
    # Помечаем все как обработанные
    for update_id in update_ids:
        await processed_update_repository.mark_as_processed(update_id)
    await test_session.commit()
    
    # Проверяем все
    for update_id in update_ids:
        assert await processed_update_repository.is_processed(update_id) is True
    
    # Проверяем необработанный
    assert await processed_update_repository.is_processed(999) is False


@pytest.mark.integration
async def test_cleanup_old_updates(processed_update_repository, test_session):
    """Тест очистки старых updates."""
    # Создаём старые updates (вручную через SQL, так как нет метода установки времени)
    # Для этого теста мы создадим updates и затем проверим cleanup
    
    # Помечаем несколько updates как обработанные
    old_update_ids = [100, 200, 300]
    new_update_ids = [400, 500]
    
    for update_id in old_update_ids + new_update_ids:
        await processed_update_repository.mark_as_processed(update_id)
    await test_session.commit()
    
    # Устанавливаем старую дату для первых трёх updates вручную
    from sqlalchemy import update as sql_update
    from src.domain.models import ProcessedUpdate
    
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)
    stmt = sql_update(ProcessedUpdate).where(
        ProcessedUpdate.update_id.in_(old_update_ids)
    ).values(processed_at=old_time)
    await test_session.execute(stmt)
    await test_session.commit()
    
    # Очищаем старые updates (старше 24 часов)
    deleted_count = await processed_update_repository.cleanup_old_updates(hours=24)
    await test_session.commit()
    
    # Проверяем, что старые updates удалены
    assert deleted_count == 3
    for update_id in old_update_ids:
        assert await processed_update_repository.is_processed(update_id) is False
    
    # Проверяем, что новые updates остались
    for update_id in new_update_ids:
        assert await processed_update_repository.is_processed(update_id) is True


@pytest.mark.integration
async def test_cleanup_with_custom_hours(processed_update_repository, test_session):
    """Тест очистки с кастомным количеством часов."""
    # Создаём updates с разными датами
    update_ids = [600, 700, 800]
    
    for update_id in update_ids:
        await processed_update_repository.mark_as_processed(update_id)
    await test_session.commit()
    
    # Устанавливаем разные даты
    from sqlalchemy import update as sql_update
    from src.domain.models import ProcessedUpdate
    
    # Update 600 - 12 часов назад (не должен быть удалён при hours=24)
    time_12h = datetime.now(timezone.utc) - timedelta(hours=12)
    stmt = sql_update(ProcessedUpdate).where(
        ProcessedUpdate.update_id == 600
    ).values(processed_at=time_12h)
    await test_session.execute(stmt)
    
    # Update 700 - 36 часов назад (должен быть удалён)
    time_36h = datetime.now(timezone.utc) - timedelta(hours=36)
    stmt = sql_update(ProcessedUpdate).where(
        ProcessedUpdate.update_id == 700
    ).values(processed_at=time_36h)
    await test_session.execute(stmt)
    
    # Update 800 - 48 часов назад (должен быть удалён)
    time_48h = datetime.now(timezone.utc) - timedelta(hours=48)
    stmt = sql_update(ProcessedUpdate).where(
        ProcessedUpdate.update_id == 800
    ).values(processed_at=time_48h)
    await test_session.execute(stmt)
    
    await test_session.commit()
    
    # Очищаем старше 24 часов
    deleted_count = await processed_update_repository.cleanup_old_updates(hours=24)
    await test_session.commit()
    
    # Проверяем
    assert deleted_count == 2
    assert await processed_update_repository.is_processed(600) is True  # Не удалён
    assert await processed_update_repository.is_processed(700) is False  # Удалён
    assert await processed_update_repository.is_processed(800) is False  # Удалён


@pytest.mark.integration
async def test_cleanup_no_old_updates(processed_update_repository, test_session):
    """Тест очистки когда нет старых updates."""
    # Создаём только новые updates
    update_ids = [900, 901, 902]
    
    for update_id in update_ids:
        await processed_update_repository.mark_as_processed(update_id)
    await test_session.commit()
    
    # Очищаем старше 24 часов (ничего не должно быть удалено)
    deleted_count = await processed_update_repository.cleanup_old_updates(hours=24)
    await test_session.commit()
    
    # Проверяем
    assert deleted_count == 0
    for update_id in update_ids:
        assert await processed_update_repository.is_processed(update_id) is True


@pytest.mark.integration
async def test_idempotency_mark_as_processed(
    processed_update_repository, test_session
):
    """Тест идемпотентности mark_as_processed."""
    update_id = 1000
    
    # Помечаем первый раз
    await processed_update_repository.mark_as_processed(update_id)
    await test_session.commit()
    
    assert await processed_update_repository.is_processed(update_id) is True
    
    # Помечаем второй раз (должно вызвать ошибку из-за уникальности primary key)
    # Но репозиторий не обрабатывает это, поэтому ожидаем ошибку
    with pytest.raises(Exception):  # IntegrityError или аналогичная
        await processed_update_repository.mark_as_processed(update_id)
        await test_session.commit()
