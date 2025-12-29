#!/bin/bash
# Скрипт для запуска приёмочных тестов

set -e

echo "🧪 Запуск приёмочных тестов..."
echo ""

# Проверяем доступность контейнеров
WEB_AVAILABLE=$(curl -sk -o /dev/null -w "%{http_code}" "https://localhost/api/health" 2>/dev/null || echo "000")
BOT_AVAILABLE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/api/health" 2>/dev/null || echo "000")

if [ "$WEB_AVAILABLE" != "200" ] || [ "$BOT_AVAILABLE" != "200" ]; then
    echo "❌ Контейнеры недоступны!"
    echo "   Web: $WEB_AVAILABLE (ожидается 200)"
    echo "   Bot: $BOT_AVAILABLE (ожидается 200)"
    echo ""
    echo "Запустите контейнеры командой: docker compose up -d"
    exit 1
fi

echo "✅ Контейнеры доступны"
echo ""

# Запускаем приёмочные тесты
pytest tests/acceptance/ -v --tb=short 2>&1

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Приёмочные тесты не прошли!"
    exit 1
fi

echo ""
echo "✅ Все приёмочные тесты прошли успешно!"
