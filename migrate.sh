#!/bin/bash
# Скрипт для управления миграциями базы данных

set -e

# Загрузка переменных окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Получение DATABASE_URL из config.json если не задан в окружении
if [ -z "$DATABASE_URL" ]; then
    DATABASE_URL=$(python3 -c "import json; print(json.load(open('config.json'))['database']['url'])")
fi

# Функция для вывода справки
show_help() {
    echo "Использование: ./migrate.sh [команда]"
    echo ""
    echo "Команды:"
    echo "  up              - Применить все непримененные миграции"
    echo "  down            - Откатить последнюю миграцию"
    echo "  status          - Показать статус миграций"
    echo "  create [name]   - Создать новую миграцию"
    echo "  reset           - Откатить все миграции и применить заново"
    echo "  help            - Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  ./migrate.sh up"
    echo "  ./migrate.sh create add_new_field"
    echo "  ./migrate.sh status"
}

# Проверка наличия команды
if [ -z "$1" ]; then
    show_help
    exit 0
fi

# Выполнение команды
case "$1" in
    up)
        echo "Применение миграций..."
        goose -dir migrations postgres "$DATABASE_URL" up
        echo "✓ Миграции применены успешно"
        ;;
    down)
        echo "Откат последней миграции..."
        goose -dir migrations postgres "$DATABASE_URL" down
        echo "✓ Миграция откачена"
        ;;
    status)
        echo "Статус миграций:"
        goose -dir migrations postgres "$DATABASE_URL" status
        ;;
    create)
        if [ -z "$2" ]; then
            echo "Ошибка: укажите название миграции"
            echo "Пример: ./migrate.sh create add_new_field"
            exit 1
        fi
        goose -dir migrations create "$2" sql
        echo "✓ Миграция создана"
        ;;
    reset)
        echo "Откат всех миграций..."
        goose -dir migrations postgres "$DATABASE_URL" reset
        echo "Применение всех миграций..."
        goose -dir migrations postgres "$DATABASE_URL" up
        echo "✓ База данных пересоздана"
        ;;
    help)
        show_help
        ;;
    *)
        echo "Неизвестная команда: $1"
        show_help
        exit 1
        ;;
esac
