#!/usr/bin/env python3
"""
Тесты для механики куража (morale)
"""

import pytest
from decimal import Decimal
import tempfile
import os
from db.models import GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field
from core.game_engine import GameEngine


class TestMoraleSystem:
    """Тесты для системы куража"""

    def test_initial_morale_is_neutral(self, db_session):
        """Тест, что изначальный кураж равен 100 (нейтральный, коэффициент 1.0)"""
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
                damage=40,
                defense=5,
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

            # Проверить, что игра создана
            assert game is not None, "Игра должна быть создана"

            # Проверить, что кураж всех юнитов изначально равен 100
            for battle_unit in game.battle_units:
                assert battle_unit.morale == 100, f"Изначальный кураж должен быть 100, но получено: {battle_unit.morale}"

        finally:
            # Удалить временный файл
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_morale_increases_when_killing_units(self, db_session):
        """Тест, что кураж повышается до 110 при убийстве юнита"""
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
            # Создать юнита с высоким уроном
            unit = Unit(
                name="Warrior",
                icon="⚔️",
                price=Decimal("100"),
                damage=100,
                defense=0,
                health=50,
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

            # Создать боевых юнитов
            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=1,
                remaining_hp=50,
                morale=100,
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
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            # Выполнить атаку, которая убьет юнита
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить, что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить, что кураж атакующего увеличился до 110
            db_session.refresh(battle_unit1)
            assert battle_unit1.morale == 110, f"Кураж атакующего должен быть 110, но получено: {battle_unit1.morale}"

        finally:
            # Удалить временный файл
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_morale_decreases_when_losing_units(self, db_session):
        """Тест, что кураж понижается до 90 при потере юнита"""
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
                damage=60,
                defense=0,
                health=50,
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
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=2)  # 2 юнита
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

            # Создать боевых юнитов
            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=1,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=2,  # 2 юнита
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            # Выполнить атаку, которая убьет одного юнита из группы
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить, что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить, что у защищающегося остался хотя бы один юнит
            db_session.refresh(battle_unit2)
            assert battle_unit2.total_count > 0, "У защищающегося должен остаться хотя бы один юнит"

            # Проверить, что кураж защищающегося понизился до 90
            assert battle_unit2.morale == 90, f"Кураж защищающегося должен быть 90, но получено: {battle_unit2.morale}"

        finally:
            # Удалить временный файл
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
