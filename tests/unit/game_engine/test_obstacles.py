#!/usr/bin/env python3
"""
Тесты для препятствий и линии видимости
"""

import pytest
from decimal import Decimal
from db.models import GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field, Obstacle
from core.game_engine import GameEngine


class TestObstacles:
    """Тесты для препятствий"""

    def test_obstacles_generated_on_game_creation(self, db_session):
        """Тест генерации препятствий при создании игры"""
        import os
        import tempfile

        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создать юнита
            unit = Unit(
                name="Warrior",
                icon="⚔️",
                price=Decimal("100"),
                damage=10,
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=1)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Создать игру через движок
            engine = GameEngine(db_session)
            game, message = engine.create_game(player1.id, "Player2", "5x5")
        finally:
            # Удалить временный файл
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

        # Проверить, что игра создана
        assert game is not None, "Игра должна быть создана"

        # Проверить, что препятствия созданы
        obstacles = db_session.query(Obstacle).filter_by(game_id=game.id).all()
        assert len(obstacles) > 0, "Должны быть сгенерированы препятствия"

        # Проверить, что препятствия не находятся на позициях юнитов
        unit_positions = {(bu.position_x, bu.position_y) for bu in game.battle_units}
        for obstacle in obstacles:
            assert (obstacle.position_x, obstacle.position_y) not in unit_positions, \
                "Препятствия не должны находиться на позициях юнитов"

    def test_cannot_move_through_obstacle(self, db_session):
        """Тест невозможности пройти через препятствие"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать юнита
        unit = Unit(
            name="Warrior",
            icon="⚔️",
            price=Decimal("100"),
            damage=10,
            defense=0,
            health=100,
            range=1,
            speed=2,  # Скорость 2 для теста перемещения
            luck=Decimal("0"),
            crit_chance=Decimal("0")
        )
        db_session.add(unit)
        db_session.flush()

        # Создать юнитов игрокам
        user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=1)
        db_session.add(user_unit1)
        db_session.flush()

        # Создать поле и игру
        field = Field(name="5x5", width=5, height=5)
        db_session.add(field)
        db_session.flush()

        game = Game(
            player1_id=player1.id,
            player2_id=player2.id,
            field_id=field.id,
            status=GameStatus.IN_PROGRESS,
            current_player_id=player1.id
        )
        db_session.add(game)
        db_session.flush()

        # Создать юнита на поле
        battle_unit = BattleUnit(
            game_id=game.id,
            user_unit_id=user_unit1.id,
            player_id=player1.id,
            position_x=0,
            position_y=0,
            total_count=1,
            remaining_hp=100,
            morale=0,
            fatigue=0,
            has_moved=0
        )
        db_session.add(battle_unit)
        db_session.flush()

        # Создать препятствие на пути
        obstacle = Obstacle(
            game_id=game.id,
            position_x=1,
            position_y=0
        )
        db_session.add(obstacle)
        db_session.flush()

        # Попытаться переместиться на клетку с препятствием
        engine = GameEngine(db_session)
        success, message, turn_switched = engine.move_unit(game.id, player1.id, battle_unit.id, 1, 0)

        # Проверить, что перемещение не удалось
        assert not success, "Перемещение на клетку с препятствием должно быть запрещено"
        assert "препятствие" in message.lower(), "Сообщение должно содержать информацию о препятствии"


class TestLineOfSight:
    """Тесты для проверки линии видимости"""

    def test_cannot_attack_through_unit(self, db_session):
        """Тест невозможности атаковать через другого юнита"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать юнита с большой дальностью
        unit = Unit(
            name="Archer",
            icon="🏹",
            price=Decimal("100"),
            damage=10,
            defense=0,
            health=100,
            range=5,  # Большая дальность
            speed=1,
            luck=Decimal("0"),
            crit_chance=Decimal("0")
        )
        db_session.add(unit)
        db_session.flush()

        # Создать юнитов игрокам
        user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=1)
        user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=1)
        user_unit3 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=1)
        db_session.add_all([user_unit1, user_unit2, user_unit3])
        db_session.flush()

        # Создать поле и игру
        field = Field(name="5x5", width=5, height=5)
        db_session.add(field)
        db_session.flush()

        game = Game(
            player1_id=player1.id,
            player2_id=player2.id,
            field_id=field.id,
            status=GameStatus.IN_PROGRESS,
            current_player_id=player1.id
        )
        db_session.add(game)
        db_session.flush()

        # Создать юнитов на одной линии: player1 (0,0), player2 (1,0), player2 (2,0)
        battle_unit1 = BattleUnit(
            game_id=game.id,
            user_unit_id=user_unit1.id,
            player_id=player1.id,
            position_x=0,
            position_y=0,
            total_count=1,
            remaining_hp=100,
            morale=0,
            fatigue=0,
            has_moved=0
        )
        battle_unit2 = BattleUnit(
            game_id=game.id,
            user_unit_id=user_unit2.id,
            player_id=player2.id,
            position_x=1,
            position_y=0,
            total_count=1,
            remaining_hp=100,
            morale=0,
            fatigue=0,
            has_moved=0
        )
        battle_unit3 = BattleUnit(
            game_id=game.id,
            user_unit_id=user_unit3.id,
            player_id=player2.id,
            position_x=2,
            position_y=0,
            total_count=1,
            remaining_hp=100,
            morale=0,
            fatigue=0,
            has_moved=0
        )
        db_session.add_all([battle_unit1, battle_unit2, battle_unit3])
        db_session.flush()

        # Попытаться атаковать юнита на (2,0) с (0,0) через юнита на (1,0)
        engine = GameEngine(db_session)
        success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit3.id)

        # Проверить, что атака не удалась
        assert not success, "Атака через другого юнита должна быть запрещена"
        assert "линии видимости" in message.lower() or "препятствие" in message.lower() or "юнит" in message.lower(), \
            "Сообщение должно содержать информацию о блокировке линии видимости"

    def test_can_attack_diagonally(self, db_session):
        """Тест возможности атаковать по диагонали при достаточной дальности"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать юнита с дальностью 3 (манхэттенское расстояние)
        unit = Unit(
            name="Archer",
            icon="🏹",
            price=Decimal("100"),
            damage=10,
            defense=0,
            health=100,
            range=3,
            speed=1,
            luck=Decimal("0"),
            crit_chance=Decimal("0")
        )
        db_session.add(unit)
        db_session.flush()

        # Создать юнитов игрокам
        user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=1)
        user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=1)
        db_session.add_all([user_unit1, user_unit2])
        db_session.flush()

        # Создать поле и игру
        field = Field(name="5x5", width=5, height=5)
        db_session.add(field)
        db_session.flush()

        game = Game(
            player1_id=player1.id,
            player2_id=player2.id,
            field_id=field.id,
            status=GameStatus.IN_PROGRESS,
            current_player_id=player1.id
        )
        db_session.add(game)
        db_session.flush()

        # Создать юнитов по диагонали: player1 (0,0), player2 (1,1)
        battle_unit1 = BattleUnit(
            game_id=game.id,
            user_unit_id=user_unit1.id,
            player_id=player1.id,
            position_x=0,
            position_y=0,
            total_count=1,
            remaining_hp=100,
            morale=0,
            fatigue=0,
            has_moved=0
        )
        battle_unit2 = BattleUnit(
            game_id=game.id,
            user_unit_id=user_unit2.id,
            player_id=player2.id,
            position_x=1,
            position_y=1,
            total_count=1,
            remaining_hp=100,
            morale=0,
            fatigue=0,
            has_moved=0
        )
        db_session.add_all([battle_unit1, battle_unit2])
        db_session.flush()

        # Попытаться атаковать по диагонали
        engine = GameEngine(db_session)
        success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

        # Проверить, что атака удалась (манхэттенское расстояние 2, в пределах дальности 3)
        assert success, f"Атака по диагонали должна быть разрешена, но получено: {message}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
