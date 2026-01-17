"""E2E тесты для потоков управления тренажёрами."""
import pytest
from unittest.mock import AsyncMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from src.domain.models import User, MuscleZone, Muscle, Machine, MachineLibrary
from src.infrastructure.web.handlers.machine.states import MachineStates

from tests.e2e.conftest import create_callback_query_update


@pytest.mark.e2e
async def test_finish_machine_creation_saves_zones_and_muscles(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест сохранения зон/мышц при создании тренажёра."""
    # Зарегистрированный пользователь
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)

    zone = MuscleZone(name="Test Zone")
    muscle = Muscle(name="Test Muscle")
    await container.muscle_repository().add_muscle_zone(zone)
    await container.muscle_repository().add(muscle)
    await test_session.commit()

    # FSM данные для завершения создания
    key = StorageKey(bot_id=bot.id or 0, chat_id=test_user_id, user_id=test_user_id)
    state = FSMContext(storage=dispatcher.storage, key=key)
    await state.set_state(MachineStates.waiting_for_muscle_selection)
    await state.update_data(
        machine_name="Bench Press",
        selected_zone_ids=[zone.id],
        selected_muscle_ids=[muscle.id],
    )

    update = create_callback_query_update(
        "finish_machine_creation",
        user_id=test_user_id,
    )

    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()

    await dispatcher.feed_update(bot, update)

    test_session.expire_all()
    created = await container.machine_repository().get_user_machine_by_name(
        test_user_id, "Bench Press"
    )
    assert created is not None
    assert {z.id for z in created.zones} == {zone.id}
    assert {m.id for m in created.muscles} == {muscle.id}


@pytest.mark.e2e
async def test_edit_machine_saves_zones_and_muscles(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест сохранения зон/мышц при редактировании тренажёра."""
    # Зарегистрированный пользователь
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)

    zone_old = MuscleZone(name="Old Zone")
    zone_new = MuscleZone(name="New Zone")
    muscle_old = Muscle(name="Old Muscle")
    muscle_new = Muscle(name="New Muscle")
    await container.muscle_repository().add_muscle_zone(zone_old)
    await container.muscle_repository().add_muscle_zone(zone_new)
    await container.muscle_repository().add(muscle_old)
    await container.muscle_repository().add(muscle_new)
    await test_session.commit()

    machine = Machine(name="Test Machine", user_id=test_user_id)
    await container.machine_repository().add_machine_with_tags(
        machine, [zone_old.id], [muscle_old.id]
    )
    await test_session.commit()

    # FSM данные для сохранения
    key = StorageKey(bot_id=bot.id or 0, chat_id=test_user_id, user_id=test_user_id)
    state = FSMContext(storage=dispatcher.storage, key=key)
    await state.set_state(MachineStates.waiting_for_edit_muscle_selection)
    await state.update_data(
        editing_machine_id=machine.id,
        selected_zone_ids=[zone_new.id],
        selected_muscle_ids=[muscle_new.id],
    )

    update = create_callback_query_update(
        "save_machine_muscles",
        user_id=test_user_id,
    )

    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    bot.send_message = AsyncMock()

    await dispatcher.feed_update(bot, update)

    test_session.expire_all()
    updated = await container.machine_repository().get_by_id(machine.id)
    assert updated is not None
    assert {z.id for z in updated.zones} == {zone_new.id}
    assert {m.id for m in updated.muscles} == {muscle_new.id}


@pytest.mark.e2e
async def test_add_machine_from_library_copies_tags(
    bot, dispatcher, container, test_session, test_user_id
):
    """Тест добавления тренажёра из библиотеки."""
    user = User(
        id=test_user_id,
        telegram_id=test_user_id,
        telegram_username="test_user",
        telegram_firstname="Test",
        telegram_lastname="User",
        is_registered=True,
    )
    await container.user_repository().add(user)

    zone = MuscleZone(name="Test Zone")
    muscle = Muscle(name="Test Muscle")
    await container.muscle_repository().add_muscle_zone(zone)
    await container.muscle_repository().add(muscle)
    await test_session.commit()

    library_machine = MachineLibrary(name_ru="Bench Press")
    library_machine.zones.append(zone)
    library_machine.muscles.append(muscle)
    await container.machine_library_repository().add(library_machine)
    await test_session.commit()

    update = create_callback_query_update(
        f"add_library_machine_{library_machine.id}",
        user_id=test_user_id,
    )
    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()

    await dispatcher.feed_update(bot, update)

    test_session.expire_all()
    created = await container.machine_repository().get_user_machine_by_name(
        test_user_id, "Bench Press"
    )
    assert created is not None
    assert created.library_machine_id == library_machine.id
    assert {z.id for z in created.zones} == {zone.id}
    assert {m.id for m in created.muscles} == {muscle.id}
