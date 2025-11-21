#!/bin/bash

# Скрипт для запуска интеграционных тестов с Docker

set -e

echo "🚀 Запуск тестовой базы данных PostgreSQL..."
docker-compose -f docker-compose.test.yml up -d

echo "⏳ Ожидание готовности базы данных..."
sleep 5

# Проверка что контейнер запущен
if ! docker-compose -f docker-compose.test.yml ps | grep -q "Up"; then
    echo "❌ Ошибка: контейнер с базой данных не запустился"
    docker-compose -f docker-compose.test.yml logs
    exit 1
fi

echo "✅ База данных готова"

# Загрузка переменных окружения для тестов
if [ -f .env.test ]; then
    export $(cat .env.test | grep -v '^#' | xargs)
fi

echo "🧪 Запуск тестов..."
pytest -v "$@"

TEST_EXIT_CODE=$?

echo ""
echo "🛑 Остановка тестовой базы данных..."
docker-compose -f docker-compose.test.yml down

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Все тесты прошли успешно!"
else
    echo "❌ Некоторые тесты не прошли (код выхода: $TEST_EXIT_CODE)"
fi

exit $TEST_EXIT_CODE
