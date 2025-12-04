FROM python:3.8-slim

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование requirements.txt и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY bot.py .
COPY game_engine.py .
COPY field_renderer.py .
COPY admin_app.py .
COPY config.json .
COPY VERSION .

# Копирование Python модуля db (модели и репозиторий)
COPY db/ ./db/

# Копирование .git для получения информации о коммитах
COPY .git/ ./.git/

# Создание директории для статических файлов (картинки юнитов)
RUN mkdir -p static/unit_images

# Создание непривилегированного пользователя
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Запуск приложения
CMD ["python", "bot.py"]
