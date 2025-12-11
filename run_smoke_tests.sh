#!/bin/bash
#
# Скрипт для запуска smoke и приёмочных тестов
# Использование:
#   ./run_smoke_tests.sh           - Только smoke тесты
#   ./run_smoke_tests.sh --full    - Smoke + приёмочные тесты (проверка версий)
#

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔍 Запуск smoke тестов...${NC}"
echo ""

# Проверяем доступность контейнеров
WEB_URL=${WEB_BASE_URL:-http://localhost:80}
BOT_URL=${BOT_API_URL:-http://localhost:8080}

echo "Проверяем доступность сервисов:"
echo "  Web: $WEB_URL"
echo "  Bot API: $BOT_URL"
echo ""

# Проверяем web
if ! curl -s -o /dev/null -w "%{http_code}" "$WEB_URL/api/version" | grep -q "200"; then
    echo -e "${RED}❌ Web-интерфейс недоступен на $WEB_URL${NC}"
    echo "   Убедитесь, что контейнер web запущен"
    exit 1
fi
echo -e "${GREEN}✓ Web-интерфейс доступен${NC}"

# Проверяем bot API
if ! curl -s -o /dev/null -w "%{http_code}" "$BOT_URL/api/version" | grep -q "200"; then
    echo -e "${RED}❌ Bot API недоступен на $BOT_URL${NC}"
    echo "   Убедитесь, что контейнер app запущен"
    exit 1
fi
echo -e "${GREEN}✓ Bot API доступен${NC}"

echo ""

# Запускаем pytest
if [ "$1" == "--full" ]; then
    echo -e "${YELLOW}Запуск полных приёмочных тестов (включая проверку версий)...${NC}"
    pytest tests/test_smoke.py -v --tb=short
else
    echo -e "${YELLOW}Запуск smoke тестов...${NC}"
    pytest tests/test_smoke.py -v -k "TestWebSmoke or TestBotSmoke" --tb=short
fi

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Все smoke тесты прошли успешно!${NC}"
else
    echo ""
    echo -e "${RED}❌ Smoke тесты не прошли!${NC}"
    exit 1
fi
