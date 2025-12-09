#!/bin/bash

# Скрипт для остановки веб-интерфейса ModernHomm

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Остановка веб-интерфейса ModernHomm"
echo "========================================="

# Остановить веб-интерфейс
docker compose stop admin

echo ""
echo "✅ Веб-интерфейс остановлена!"
echo ""
echo "Для повторного запуска используйте:"
echo "  ./start_admin.sh"
echo ""
