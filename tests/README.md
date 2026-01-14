# Тесты проекта tg-training-log

## Структура

```
tests/
├── conftest.py          # Общие fixtures для всех тестов
├── unit/                # Unit тесты (быстрые, изолированные)
├── integration/         # Integration тесты (с реальной БД)
└── e2e/                 # End-to-end тесты (полный стек)
```

## Запуск тестов

### Все тесты
```bash
uv run pytest
```

### Только unit тесты
```bash
uv run pytest tests/unit/ -m unit
```

### Только integration тесты
```bash
uv run pytest tests/integration/ -m integration
```

### Только E2E тесты
```bash
uv run pytest tests/e2e/ -m e2e
```

### С покрытием кода
```bash
uv run pytest --cov=src --cov-report=html
```

### Конкретный тест
```bash
uv run pytest tests/unit/test_example.py -v
```

## Fixtures

### Тестовая БД
- `test_engine` - SQLite in-memory engine (для каждого теста)
- `test_session` - AsyncSession с автоматическим rollback

### Репозитории
- `user_repository`
- `machine_repository`
- `muscle_repository`
- `workout_session_repository`
- `set_entry_repository`
- `processed_update_repository`

### Use Cases
- `registration_use_case`
- `workout_use_case`
- `machine_management_use_case`
- `google_sheets_export_use_case` (с моком Google Sheets)

### E2E Fixtures
- `bot` - мок Bot для тестов
- `dispatcher` - Dispatcher с подключенными handlers и middlewares
- `container` - Container с тестовыми зависимостями
- `create_message_update()` - создание Update с Message
- `create_callback_query_update()` - создание Update с CallbackQuery

### Тестовые данные
- `test_user_id` - тестовый user_id
- `test_user_data` - данные для создания пользователя
- `test_machine_data` - данные для создания тренажёра

## Примеры

### Unit тест
```python
import pytest

@pytest.mark.unit
async def test_user_creation(user_repository, test_user_data):
    user = await user_repository.add(User(**test_user_data))
    assert user.id == test_user_data["id"]
```

### Integration тест
```python
import pytest

@pytest.mark.integration
async def test_workout_flow(workout_use_case, test_user_id):
    session = await workout_use_case.start_new_workout(test_user_id)
    assert session is not None
```

### E2E тест
```python
import pytest
from tests.e2e.conftest import create_message_update

@pytest.mark.e2e
async def test_start_workout_flow(bot, dispatcher, container, test_session, test_user_id):
    update = create_message_update("/workout_start", user_id=test_user_id)
    bot.send_message = AsyncMock()
    await dispatcher.feed_update(bot, update)
    assert bot.send_message.called
```

## Маркеры

- `@pytest.mark.unit` - unit тесты
- `@pytest.mark.integration` - integration тесты
- `@pytest.mark.e2e` - end-to-end тесты
- `@pytest.mark.slow` - медленные тесты

## Конфигурация

Конфигурация pytest находится в `pyproject.toml` в секции `[tool.pytest.ini_options]`.

## Покрытие кода

Целевое покрытие: **> 80%**

Текущее покрытие можно посмотреть после запуска тестов:
- HTML отчёт: `htmlcov/index.html`
- XML отчёт: `coverage.xml`
