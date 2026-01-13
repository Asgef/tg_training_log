FROM python:3.13-slim

WORKDIR /app

# Установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# Установка зависимостей
RUN uv sync --frozen --no-dev

# Копирование кода приложения
COPY . .

# Копирование Google credentials файла (если существует)
COPY tgtraining-69d93acc8e17.json* ./

# Применение миграций при старте (опционально, можно убрать если миграции применяются отдельно)
# RUN uv run alembic upgrade head

# Точка входа
CMD ["uv", "run", "python", "src/main.py"]
