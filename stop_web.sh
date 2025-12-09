#!/bin/bash

# Скрипт для остановки веб-интерфейса ModernHomm

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Остановка веб-интерфейса ModernHomm"
echo "========================================="

# Остановить веб-интерфейс
docker compose stop web

echo ""
echo "✅ Веб-интерфейс остановлен!"
echo ""
echo "Для повторного запуска используйте:"
echo "  ./start_web.sh"
echo ""
