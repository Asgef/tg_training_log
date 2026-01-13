# tg_training_log

## Описание
Этот проект представляет собой Telegram-бота для логирования тренировок. Он позволяет пользователям регистрироваться, управлять тренировочными сессиями, записывать подходы, вести справочник тренажеров и экспортировать данные в Google Sheets.

## Установка

### Prerequisites
- Python 3.10+
- Docker (для базы данных PostgreSQL)
- uv (менеджер пакетов Python)

### Шаги

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/tg_training_log.git
   cd tg_training_log
   ```

2. Установите зависимости Python:
   ```bash
   uv sync
   ```

3. Настройте переменные окружения. Создайте файл `.env` в корне проекта на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```
   Отредактируйте `.env`, добавив необходимые значения. Подробнее о переменных окружения см. ниже.

4. Запустите базу данных PostgreSQL с помощью Docker Compose:
   ```bash
   docker compose up -d postgres
   ```
   (Примечание: PostgreSQL будет доступен на порту 5433 на вашей хост-машине.)

5. Примените миграции базы данных:
   ```bash
   uv run alembic upgrade head
   ```

6. Запустите бота:
   ```bash
   uv run python src/main.py
   ```

## Переменные окружения

Файл `.env` должен содержать следующие переменные:

-   `BOT_TOKEN`: Токен вашего Telegram-бота, полученный от BotFather.
-   `DATABASE_URL`: Строка подключения к базе данных PostgreSQL. Например: `postgresql+psycopg2://user:password@localhost:5433/mydatabase`.
    -   `user`: Имя пользователя базы данных (по умолчанию `user`).
    -   `password`: Пароль пользователя базы данных (по умолчанию `password`).
    -   `localhost`: Адрес хоста базы данных. Используйте `localhost` если запускаете локально.
    -   `5433`: Порт, на котором PostgreSQL доступен на вашей хост-машине (может отличаться, если вы изменили `docker-compose.yml`).
    -   `mydatabase`: Имя базы данных (по умолчанию `mydatabase`).
-   `ADMIN_ID`: ID администратора Telegram для подтверждения регистраций. Разделяйте несколько ID запятыми (например, `12345,67890`).
-   `GOOGLE_CREDENTIALS_JSON`: JSON-строка учетных данных сервисного аккаунта Google для доступа к Google Sheets. **Важно:** Эта строка должна быть валидным JSON-объектом.

## Использование

После запуска бота найдите его в Telegram и используйте следующие команды:

-   `/start`: Начать взаимодействие с ботом, пройти регистрацию.
-   `/workout_start`: Начать новую тренировочную сессию.
-   `/workout_end`: Завершить текущую тренировочную сессию.
-   `/record_set`: Записать подход к упражнению.
-   `/machines`: Управление вашим списком тренажеров (добавление, просмотр, редактирование, архивация).
-   `/google_sheets`: Настроить экспорт данных в Google Sheets.

## Структура проекта
```
src/
├── application/         # Слой вариантов использования (use cases) и интерфейсов репозиториев
│   ├── repositories.py  # Интерфейсы репозиториев
│   ├── use_cases.py     # Интерфейсы вариантов использования
│   ├── use_cases/       # Реализации вариантов использования
│   │   ├── google_sheets_export.py
│   │   ├── machine_management.py
│   │   ├── registration.py
│   │   └── workout.py
├── configs/             # Конфигурационные файлы
│   └── logging_config.py
├── domain/              # Доменные модели (сущности)
│   └── models.py
├── infrastructure/      # Адаптеры к внешним системам
│   ├── db/              # Взаимодействие с базой данных
│   │   ├── alembic/
│   │   ├── repositories/
│   │   │   ├── machine_repository.py
│   │   │   ├── muscle_repository.py
│   │   │   ├── set_entry_repository.py
│   │   │   ├── user_repository.py
│   │   │   └── workout_session_repository.py
│   │   └── base.py
│   ├── services/        # Внешние сервисы (Google Sheets)
│   │   └── google_sheets_client.py
│   ├── web/             # Веб-интерфейс (обработчики Telegram)
│   │   ├── handlers/
│   │   │   ├── common.py
│   │   │   ├── machine.py
│   │   │   ├── registration.py
│   │   │   └── workout.py
│   │   └── middlewares.py
│   └── main.py          # Точка входа приложения
tests/                   # Тесты
scripts/                 # Вспомогательные скрипты
```

## Разработка
### Запуск тестов
```bash
uv run pytest
```

### Форматирование кода
```bash
uv run black .
uv run isort .
```

### Линтинг
```bash
uv run ruff check .
```