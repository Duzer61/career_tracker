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

# Команда для запуска приложения
CMD ["sh", "-c", ". .venv/bin/activate && python main.py"]
