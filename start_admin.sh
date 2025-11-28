#!/bin/bash

# Скрипт для запуска админки ModernHomm

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Запуск админки ModernHomm"
echo "========================================="

# Проверить, запущен ли postgres
if ! docker ps | grep -q modernhomm_postgres; then
    echo "⚠️  PostgreSQL не запущен. Запускаем..."
    docker compose up -d postgres
    echo "Ожидание готовности PostgreSQL..."
    sleep 5
fi

# Собрать образ админки если нужно
echo "Сборка образа админки..."
docker compose build admin

# Запустить админку
echo "Запуск контейнера админки..."
docker compose up -d admin

# Дождаться запуска
echo "Ожидание запуска админки..."
sleep 3

# Проверить статус
if docker ps | grep -q modernhomm_admin; then
    echo ""
    echo "========================================="
    echo "✅ Админка успешно запущена!"
    echo "========================================="
    echo ""
    echo "🌐 Доступ к админке:"
    echo "   http://localhost"
    echo ""
    echo "📊 Для просмотра логов:"
    echo "   docker compose logs -f admin"
    echo ""
    echo "🛑 Для остановки:"
    echo "   docker compose stop admin"
    echo ""
    echo "========================================="
else
    echo ""
    echo "❌ Ошибка запуска админки!"
    echo "Просмотрите логи: docker compose logs admin"
    exit 1
fi
