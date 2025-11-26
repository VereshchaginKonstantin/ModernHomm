#!/bin/bash

# Скрипт запуска контейнеров ModernHomm
# Запускает контейнеры, если они не запущены

set -e

echo "=== Запуск контейнеров ModernHomm ==="

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Ошибка: Docker не установлен"
    exit 1
fi

# Проверка существования контейнеров
if ! docker ps -a --format '{{.Names}}' | grep -q '^modernhomm_postgres$'; then
    echo "❌ Контейнер modernhomm_postgres не найден"
    echo "   Запустите сначала: ./init.sh"
    exit 1
fi

if ! docker ps -a --format '{{.Names}}' | grep -q '^modernhomm_app$'; then
    echo "❌ Контейнер modernhomm_app не найден"
    echo "   Запустите сначала: ./init.sh"
    exit 1
fi

# Проверка статуса контейнера базы данных
if docker ps --format '{{.Names}}' | grep -q '^modernhomm_postgres$'; then
    echo "ℹ️  Контейнер modernhomm_postgres уже запущен"
else
    echo "🚀 Запуск контейнера базы данных..."
fi

# Проверка статуса контейнера приложения
if docker ps --format '{{.Names}}' | grep -q '^modernhomm_app$'; then
    echo "ℹ️  Контейнер modernhomm_app уже запущен"
else
    echo "🚀 Запуск контейнера приложения..."
fi

# Запуск контейнеров
echo "▶️  Запуск контейнеров через Docker Compose..."
docker compose up -d

# Ожидание готовности базы данных
echo "⏳ Ожидание готовности базы данных..."
timeout 30 bash -c 'until docker exec modernhomm_postgres pg_isready -U postgres &> /dev/null; do sleep 1; done' || {
    echo "❌ Ошибка: База данных не готова после 30 секунд ожидания"
    exit 1
}

echo ""
echo "✅ Контейнеры успешно запущены!"
echo ""
echo "Статус контейнеров:"
docker compose ps
echo ""
echo "Просмотр логов:"
echo "  - Все логи: docker compose logs -f"
echo "  - Логи БД: docker compose logs -f postgres"
echo "  - Логи приложения: docker compose logs -f app"
