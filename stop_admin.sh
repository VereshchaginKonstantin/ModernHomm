#!/bin/bash

# Скрипт для остановки админки ModernHomm

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Остановка админки ModernHomm"
echo "========================================="

# Остановить админку
docker compose stop admin

echo ""
echo "✅ Админка остановлена!"
echo ""
echo "Для повторного запуска используйте:"
echo "  ./start_admin.sh"
echo ""
