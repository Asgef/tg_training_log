"""Integration тесты для MachineLibraryRepository."""
import pytest

from src.domain.models import MachineLibrary, MachineLibraryAlias, MuscleZone, Muscle


@pytest.mark.integration
async def test_search_library_machines(
    machine_library_repository, test_session
):
    """Тест поиска по названию и алиасу."""
    library_machine = MachineLibrary(name_ru="Жим лёжа")
    library_machine.aliases.append(MachineLibraryAlias(alias="Bench Press"))
    await machine_library_repository.add(library_machine)
    await test_session.commit()

    by_name = await machine_library_repository.search_library_machines("Жим")
    assert len(by_name) == 1
    assert by_name[0].name_ru == "Жим лёжа"

    by_alias = await machine_library_repository.search_library_machines("bench")
    assert len(by_alias) == 1
    assert by_alias[0].name_ru == "Жим лёжа"


@pytest.mark.integration
async def test_get_library_machine_with_tags(
    machine_library_repository, test_session
):
    """Тест получения зон и мышц из библиотеки."""
    zone = MuscleZone(name="Грудь")
    muscle = Muscle(name="Большая грудная")
    test_session.add_all([zone, muscle])
    await test_session.commit()

    library_machine = MachineLibrary(name_ru="Жим лёжа")
    library_machine.zones.append(zone)
    library_machine.muscles.append(muscle)
    await machine_library_repository.add(library_machine)
    await test_session.commit()

    fetched = await machine_library_repository.get_library_machine_by_id(
        library_machine.id
    )
    assert fetched is not None
    assert {z.id for z in fetched.zones} == {zone.id}
    assert {m.id for m in fetched.muscles} == {muscle.id}
