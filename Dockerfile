FROM python:3.13-slim

WORKDIR /app

# Установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# Установка зависимостей
RUN uv sync --frozen --no-dev

# Копирование кода приложения (сохраняем структуру src/)
COPY src/ ./src/

# Копирование конфигурационных файлов
COPY alembic.ini ./

# Копирование Google credentials файла (если существует)
COPY tgtraining-69d93acc8e17.json* ./

# Установка PYTHONPATH для корректных импортов
ENV PYTHONPATH=/app

# Применение миграций при старте (опционально, можно убрать если миграции применяются отдельно)
# RUN uv run alembic upgrade head

# Точка входа
CMD ["uv", "run", "python", "src/main.py"]
