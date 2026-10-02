FROM python:3.14-slim

WORKDIR /app

# Установка uv и bash (для лучшей совместимости)
RUN pip install uv && \
    apt-get update && \
    apt-get install -y bash curl && \
    rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей (pyproject + lock — воспроизводимая сборка)
COPY pyproject.toml uv.lock ./

# Установка зависимостей строго по uv.lock (как в CI и тестах)
RUN uv venv && \
    . .venv/bin/activate && \
    uv sync --frozen --no-install-project

# Копирование всего приложения (пакет app импортируется из рабочей директории /app)
COPY . .

# Создание entrypoint скрипта с автоматическими миграциями
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Activating virtual environment..."\n\
. .venv/bin/activate\n\
echo "Running database migrations..."\n\
alembic upgrade head\n\
echo "Starting application..."\n\
exec python main.py' > /entrypoint.sh && chmod +x /entrypoint.sh

# Используем entrypoint вместо cmd
ENTRYPOINT ["/entrypoint.sh"]
