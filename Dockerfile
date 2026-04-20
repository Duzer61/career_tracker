FROM python:3.14-slim

WORKDIR /app

# Установка uv и bash (для лучшей совместимости)
RUN pip install uv && \
    apt-get update && \
    apt-get install -y bash && \
    rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY pyproject.toml ./

# Установка зависимостей (упрощенный способ)
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e .

# Копирование всего приложения
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
