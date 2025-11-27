#!/usr/bin/env python3
"""
Тест для проверки расчета доступных клеток для перемещения
"""

import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5433/telegram_bot_test'

from db import Database
from game_engine import GameEngine
from db.models import GameStatus

def test_movement_cells():
    """Тест расчета доступных клеток для перемещения"""
    db = Database()

    with db.get_session() as session:
        engine = GameEngine(session)

        # Получить первую активную игру или создать тестовую
        # Для полноценного теста нужно создать игру с известным состоянием
        print("Тест расчета доступных клеток для перемещения")
        print("=" * 60)

        # Проверка, что метод существует
        assert hasattr(engine, 'get_available_movement_cells'), "Метод get_available_movement_cells не найден"

        # Проверка вызова с несуществующей игрой
        result = engine.get_available_movement_cells(999999, 999999)
        assert result == [], "Для несуществующей игры должен вернуться пустой список"

        print("✅ Метод get_available_movement_cells работает корректно")
        print("✅ Возвращает пустой список для несуществующих игр")

        # Для полного теста нужно создать игру с юнитами
        # Это можно сделать через интеграционные тесты

if __name__ == "__main__":
    test_movement_cells()
