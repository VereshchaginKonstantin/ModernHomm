#!/usr/bin/env python3
"""
Миграция: добавление колонки icon в таблицу units
"""

import os
import json
from sqlalchemy import create_engine, text

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

def migrate():
    """Выполнение миграции"""
    db_url = get_database_url()
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Проверяем, существует ли колонка
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='units' AND column_name='icon'
        """))

        if result.fetchone() is None:
            print("Добавляем колонку 'icon' в таблицу 'units'...")
            conn.execute(text("""
                ALTER TABLE units
                ADD COLUMN icon VARCHAR(10) NOT NULL DEFAULT '🎮'
            """))
            conn.commit()
            print("✓ Колонка 'icon' успешно добавлена")
        else:
            print("Колонка 'icon' уже существует в таблице 'units'")

if __name__ == '__main__':
    migrate()
    print("Миграция завершена!")
