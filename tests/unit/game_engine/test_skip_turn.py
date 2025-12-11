#!/usr/bin/env python3
"""
Тесты для пропуска хода юнитом
"""

import pytest
import tempfile
import os
from decimal import Decimal
from db.models import GameUser, Unit, UserUnit, BattleUnit, Game, GameStatus, Field
from core.game_engine import GameEngine


class TestSkipTurn:
    """Тесты для пропуска хода"""

    def test_skip_unit_turn(self, db_session):
        """Тест, что можно пропустить ход юнита"""
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
            # Создать юнита
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

            # Создать боевого юнита игрока 1
            battle_unit = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=1,
                remaining_hp=100,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add(battle_unit)
            db_session.flush()

            # Создать боевого юнита игрока 2
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=4,
                position_y=4,
                total_count=1,
                remaining_hp=100,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add(battle_unit2)
            db_session.flush()

            # Проверить что юнит не ходил
            assert battle_unit.has_moved == False, "Юнит не должен был ходить"

            # Пропустить ход юнита
            game_engine = GameEngine(db_session)
            success, msg, turn_switched = game_engine.skip_unit_turn(game.id, player1.id, battle_unit.id)

            # Проверить успех
            assert success is True, f"Пропуск хода должен быть успешным, получено: {msg}"
            assert "пропущен" in msg.lower(), "Сообщение должно содержать информацию о пропуске хода"

            # Проверить что юнит помечен как ходивший
            db_session.refresh(battle_unit)
            assert battle_unit.has_moved == True, "Юнит должен быть помечен как ходивший"

            # Проверить смену хода (у игрока 1 только один юнит)
            assert turn_switched is True, "Ход должен был смениться"
            db_session.refresh(game)
            assert game.current_player_id == player2.id, "Ход должен перейти к игроку 2"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_skip_already_moved_unit(self, db_session):
        """Тест, что нельзя пропустить ход юнита, который уже ходил"""
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
            # Создать юнита
            unit = Unit(
                name="Тестовый юнит 2",
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

            # Создать поле и игру
            field = Field(name="5x5 v2", width=5, height=5)
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

            # Создать боевого юнита игрока 1
            battle_unit = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=1,
                remaining_hp=100,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add(battle_unit)
            db_session.flush()

            # Пропустить ход юнита первый раз
            game_engine = GameEngine(db_session)
            success, msg, _ = game_engine.skip_unit_turn(game.id, player1.id, battle_unit.id)
            assert success is True, f"Первый пропуск хода должен быть успешным, получено: {msg}"

            # Попытаться пропустить ход снова
            success, msg, _ = game_engine.skip_unit_turn(game.id, player2.id, battle_unit.id)

            # Проверить что второй пропуск не удался
            assert success is False, "Повторный пропуск хода должен завершиться неудачей"
            assert any(phrase in msg.lower() for phrase in ["не ваш ход", "уже совершил ход", "не ваш юнит"]), f"Сообщение должно указывать на ошибку, получено: {msg}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_skip_wrong_player_unit(self, db_session):
        """Тест, что нельзя пропустить ход чужого юнита"""
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
            # Создать юнита
            unit = Unit(
                name="Тестовый юнит 3",
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

            # Создать поле и игру
            field = Field(name="5x5 v3", width=5, height=5)
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

            # Создать боевого юнита игрока 2
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=4,
                position_y=4,
                total_count=1,
                remaining_hp=100,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add(battle_unit2)
            db_session.flush()

            # Попытаться пропустить ход юнита игрока 2 от имени игрока 1
            game_engine = GameEngine(db_session)
            success, msg, _ = game_engine.skip_unit_turn(game.id, player1.id, battle_unit2.id)

            # Проверить что попытка не удалась
            assert success is False, "Попытка пропустить ход чужого юнита должна завершиться неудачей"
            assert "не ваш юнит" in msg.lower(), f"Сообщение должно указывать на то, что это не ваш юнит, получено: {msg}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
