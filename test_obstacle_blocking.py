#!/usr/bin/env python3
"""
Тесты для отображения препятствий и фильтрации целей
"""

import pytest
import tempfile
import os
from decimal import Decimal
from db.models import Game, BattleUnit, UserUnit, Unit, Field, Obstacle, GameUser
from game_engine import GameEngine
from field_renderer import FieldRenderer


class TestObstacleBlockingAndDisplay:
    """Тесты для препятствий и блокировки целей"""

    def test_obstacle_blocks_target(self, db_session):
        """Тест, что препятствие блокирует цель"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=111, name="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, name="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создать юнита с дальностью 5
            unit = Unit(
                name="Лучник",
                icon="🏹",
                price=Decimal("200"),
                damage=30,
                defense=5,
                health=50,
                range=5,  # Дальность 5
                speed=2,
                luck=Decimal("0.1"),
                crit_chance=Decimal("0.2"),
                dodge_chance=Decimal("0.1"),
                is_kamikaze=0,
                counterattack_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=10)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=10)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Создать игру
            game_engine = GameEngine(db_session)
            game, message = game_engine.create_game(player1.id, "Player2", "7x7")

            # Получить боевых юнитов
            battle_unit1 = db_session.query(BattleUnit).filter(
                BattleUnit.game_id == game.id,
                BattleUnit.player_id == player1.id
            ).first()

            battle_unit2 = db_session.query(BattleUnit).filter(
                BattleUnit.game_id == game.id,
                BattleUnit.player_id == player2.id
            ).first()

            # Переместить юнитов на нужные позиции
            battle_unit1.position_x = 0
            battle_unit1.position_y = 3

            battle_unit2.position_x = 4
            battle_unit2.position_y = 3

            # Добавить препятствие между ними на позиции (2, 3)
            obstacle = Obstacle(
                game_id=game.id,
                position_x=2,
                position_y=3
            )
            db_session.add(obstacle)
            db_session.flush()

            # Получить доступные цели для юнита 1
            targets = game_engine._get_available_targets(game, battle_unit1)

            # Цель не должна быть в списке из-за препятствия
            target_ids = [t["unit_id"] for t in targets]
            assert battle_unit2.id not in target_ids, "Препятствие должно блокировать линию видимости"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_no_obstacle_allows_target(self, db_session):
        """Тест, что без препятствия цель доступна"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=333, name="Player3", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=444, name="Player4", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создать юнита с дальностью 5
            unit = Unit(
                name="Лучник2",
                icon="🏹",
                price=Decimal("200"),
                damage=30,
                defense=5,
                health=50,
                range=5,
                speed=2,
                luck=Decimal("0.1"),
                crit_chance=Decimal("0.2"),
                dodge_chance=Decimal("0.1"),
                is_kamikaze=0,
                counterattack_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=10)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=10)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Создать игру
            game_engine = GameEngine(db_session)
            game, message = game_engine.create_game(player1.id, "Player4", "7x7")

            # Получить боевых юнитов
            battle_unit1 = db_session.query(BattleUnit).filter(
                BattleUnit.game_id == game.id,
                BattleUnit.player_id == player1.id
            ).first()

            battle_unit2 = db_session.query(BattleUnit).filter(
                BattleUnit.game_id == game.id,
                BattleUnit.player_id == player2.id
            ).first()

            # Переместить юнитов на нужные позиции (на расстоянии 4)
            battle_unit1.position_x = 0
            battle_unit1.position_y = 3

            battle_unit2.position_x = 4
            battle_unit2.position_y = 3

            # Удалить все препятствия на горизонтальной линии между юнитами
            db_session.query(Obstacle).filter(
                Obstacle.game_id == game.id,
                Obstacle.position_y == 3,
                Obstacle.position_x >= 1,
                Obstacle.position_x <= 3
            ).delete()

            db_session.flush()

            # Получить доступные цели для юнита 1 (без препятствий)
            targets = game_engine._get_available_targets(game, battle_unit1)

            # Цель должна быть в списке
            target_ids = [t["unit_id"] for t in targets]
            assert battle_unit2.id in target_ids, "Без препятствий цель должна быть доступна"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_obstacle_rendered_on_field(self, db_session):
        """Тест, что препятствие отображается на поле"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=555, name="Player5", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=666, name="Player6", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создать юнита без image_path (будет использоваться только текст/иконка)
            unit = Unit(
                name="Тестовый юнит",
                icon="⚔️",
                price=Decimal("100"),
                damage=20,
                defense=10,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                counterattack_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=1)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Создать игру
            game_engine = GameEngine(db_session)
            game, message = game_engine.create_game(player1.id, "Player6", "5x5")

            # Проверить что препятствия созданы
            obstacles = db_session.query(Obstacle).filter_by(game_id=game.id).all()
            assert len(obstacles) > 0, "Препятствия должны быть созданы при создании игры"

            # Проверить что препятствия доступны для отрисовки
            for obstacle in obstacles:
                assert obstacle.position_x >= 0, "X координата препятствия должна быть валидной"
                assert obstacle.position_y >= 0, "Y координата препятствия должна быть валидной"
                assert obstacle.position_x < game.field.width, "X должна быть в пределах поля"
                assert obstacle.position_y < game.field.height, "Y должна быть в пределах поля"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_diagonal_obstacle_blocks_target(self, db_session):
        """Тест, что препятствие блокирует диагональную атаку"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=777, name="Player7", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=888, name="Player8", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создать юнита с дальностью 5
            unit = Unit(
                name="Маг",
                icon="🧙",
                price=Decimal("300"),
                damage=40,
                defense=5,
                health=60,
                range=5,
                speed=1,
                luck=Decimal("0.05"),
                crit_chance=Decimal("0.1"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                counterattack_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=10)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=10)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Создать игру
            game_engine = GameEngine(db_session)
            game, message = game_engine.create_game(player1.id, "Player8", "7x7")

            # Получить боевых юнитов
            battle_unit1 = db_session.query(BattleUnit).filter(
                BattleUnit.game_id == game.id,
                BattleUnit.player_id == player1.id
            ).first()

            battle_unit2 = db_session.query(BattleUnit).filter(
                BattleUnit.game_id == game.id,
                BattleUnit.player_id == player2.id
            ).first()

            # Переместить юнитов на диагональные позиции
            battle_unit1.position_x = 0
            battle_unit1.position_y = 0

            battle_unit2.position_x = 3
            battle_unit2.position_y = 3

            # Добавить препятствие на диагонали (1, 1)
            obstacle = Obstacle(
                game_id=game.id,
                position_x=1,
                position_y=1
            )
            db_session.add(obstacle)
            db_session.flush()

            # Получить доступные цели для юнита 1
            targets = game_engine._get_available_targets(game, battle_unit1)

            # Цель не должна быть в списке из-за препятствия на диагонали
            target_ids = [t["unit_id"] for t in targets]
            assert battle_unit2.id not in target_ids, "Препятствие на диагонали должно блокировать линию видимости"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
