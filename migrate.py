#!/usr/bin/env python3
"""
Скрипт для управления миграциями базы данных через goose
"""

import os
import sys
import json
import subprocess


def load_config():
    """Загрузка конфигурации из config.json"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_database_url():
    """Получение URL базы данных из переменной окружения или config.json"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        config = load_config()
        db_url = config['database']['url']
    return db_url


def run_goose(command):
    """Запуск goose с указанной командой"""
    db_url = get_database_url()
    cmd = ['goose', '-dir', 'migrations', 'postgres', db_url] + command

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка: {e.stderr}")
        return False


def show_help():
    """Вывод справки"""
    print("""Использование: python3 migrate.py [команда]

Команды:
  up              - Применить все непримененные миграции
  down            - Откатить последнюю миграцию
  status          - Показать статус миграций
  create [name]   - Создать новую миграцию
  reset           - Откатить все миграции и применить заново
  help            - Показать эту справку

Примеры:
  python3 migrate.py up
  python3 migrate.py create add_new_field
  python3 migrate.py status
""")


def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1]

    if command == 'up':
        print("Применение миграций...")
        if run_goose(['up']):
            print("✓ Миграции применены успешно")

    elif command == 'down':
        print("Откат последней миграции...")
        if run_goose(['down']):
            print("✓ Миграция откачена")

    elif command == 'status':
        print("Статус миграций:")
        run_goose(['status'])

    elif command == 'create':
        if len(sys.argv) < 3:
            print("Ошибка: укажите название миграции")
            print("Пример: python3 migrate.py create add_new_field")
            sys.exit(1)

        migration_name = sys.argv[2]
        subprocess.run(['goose', '-dir', 'migrations', 'create', migration_name, 'sql'])
        print("✓ Миграция создана")

    elif command == 'reset':
        print("Откат всех миграций...")
        run_goose(['reset'])
        print("Применение всех миграций...")
        if run_goose(['up']):
            print("✓ База данных пересоздана")

    elif command == 'help':
        show_help()

    else:
        print(f"Неизвестная команда: {command}")
        show_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
