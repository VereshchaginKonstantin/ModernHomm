#!/usr/bin/env python3
"""
Тесты для механики контратаки (counterattack_chance)
"""

import pytest
from decimal import Decimal
import tempfile
import os
from db.models import GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field
from core.game_engine import GameEngine


class TestCounterattackSystem:
    """Тесты для системы контратаки"""

    def test_unit_with_zero_counterattack_does_not_counterattack(self, db_session):
        """Тест, что юнит с counterattack_chance=0 не контратакует"""
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
            # Создать атакующего юнита
            attacker_unit = Unit(
                name="Attacker",
                icon="⚔️",
                price=Decimal("100"),
                damage=50,
                defense=0,
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

            # Создать защищающегося юнита без контратаки
            defender_unit = Unit(
                name="Defender",
                icon="🛡️",
                price=Decimal("100"),
                damage=30,
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                counterattack_chance=Decimal("0"),  # Нет контратаки
                image_path=temp_image_path
            )
            db_session.add_all([attacker_unit, defender_unit])
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=attacker_unit.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=defender_unit.id, count=1)
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
                remaining_hp=100,
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
                remaining_hp=100,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            attacker_initial_hp = battle_unit1.remaining_hp

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить что атакующий не получил урон (контратаки нет)
            db_session.refresh(battle_unit1)
            assert battle_unit1.remaining_hp == attacker_initial_hp, \
                "Атакующий не должен получить урон (контратаки нет)"

            # Проверить что в логе нет упоминания контратаки
            assert "КОНТРАТАКА" not in message and "контратак" not in message.lower(), \
                "Лог не должен содержать информацию о контратаке"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_unit_with_counterattack_deals_damage_back(self, db_session):
        """Тест, что юнит с контратакой наносит ответный урон"""
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
            # Создать атакующего юнита
            attacker_unit = Unit(
                name="Attacker",
                icon="⚔️",
                price=Decimal("100"),
                damage=50,
                defense=0,
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

            # Создать защищающегося юнита с 50% контратакой
            defender_unit = Unit(
                name="Defender",
                icon="🛡️",
                price=Decimal("100"),
                damage=40,  # Базовый урон
                defense=0,
                health=200,  # Много HP чтобы выжить
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                counterattack_chance=Decimal("0.5"),  # 50% контратака
                image_path=temp_image_path
            )
            db_session.add_all([attacker_unit, defender_unit])
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=attacker_unit.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=defender_unit.id, count=1)
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
                remaining_hp=100,
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
                remaining_hp=200,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            attacker_initial_hp = battle_unit1.remaining_hp

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить что атакующий получил урон от контратаки
            db_session.refresh(battle_unit1)
            counterattack_damage = attacker_initial_hp - battle_unit1.remaining_hp

            # Ожидаемый урон контратаки: 40 * 0.5 = 20
            expected_damage = 20
            assert counterattack_damage == expected_damage, \
                f"Ожидаемый урон контратаки {expected_damage}, получено {counterattack_damage}"

            # Проверить что в логе есть информация о контратаке
            assert "КОНТРАТАКА" in message or "контратак" in message.lower(), \
                "Лог должен содержать информацию о контратаке"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_counterattack_respects_unit_count(self, db_session):
        """Тест, что контратака учитывает количество юнитов"""
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
            # Создать атакующего юнита
            attacker_unit = Unit(
                name="Attacker",
                icon="⚔️",
                price=Decimal("100"),
                damage=30,
                defense=0,
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

            # Создать защищающегося юнита с контратакой
            defender_unit = Unit(
                name="Defender",
                icon="🛡️",
                price=Decimal("100"),
                damage=10,  # Малый базовый урон
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                counterattack_chance=Decimal("1.0"),  # 100% контратака
                image_path=temp_image_path
            )
            db_session.add_all([attacker_unit, defender_unit])
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=attacker_unit.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=defender_unit.id, count=3)
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

            # Создать боевых юнитов - у защитника 3 юнита
            battle_unit1 = BattleUnit(
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
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=3,  # 3 защищающихся юнита
                remaining_hp=100,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            attacker_initial_hp = battle_unit1.remaining_hp

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить что урон контратаки учитывает количество юнитов
            db_session.refresh(battle_unit1)
            counterattack_damage = attacker_initial_hp - battle_unit1.remaining_hp

            # Ожидаемый урон контратаки: 10 * 3 юнита * 1.0 = 30
            expected_damage = 30
            assert counterattack_damage == expected_damage, \
                f"Ожидаемый урон контратаки {expected_damage} (10 x 3 юнита x 1.0), получено {counterattack_damage}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_no_counterattack_if_defender_dies(self, db_session):
        """Тест, что контратака не происходит если защитник убит"""
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
            # Создать атакующего юнита с большим уроном
            attacker_unit = Unit(
                name="Attacker",
                icon="⚔️",
                price=Decimal("100"),
                damage=1000,  # Огромный урон
                defense=0,
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

            # Создать слабого защитника с контратакой
            defender_unit = Unit(
                name="Defender",
                icon="🛡️",
                price=Decimal("100"),
                damage=50,
                defense=0,
                health=10,  # Малое HP
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                counterattack_chance=Decimal("1.0"),  # 100% контратака
                image_path=temp_image_path
            )
            db_session.add_all([attacker_unit, defender_unit])
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=attacker_unit.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=defender_unit.id, count=1)
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
                remaining_hp=100,
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
                remaining_hp=10,  # Малое HP
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            attacker_initial_hp = battle_unit1.remaining_hp

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить что защитник убит
            defender_exists = db_session.query(BattleUnit).filter_by(id=battle_unit2.id).first()
            assert defender_exists is None, "Защитник должен быть убит"

            # Проверить что атакующий не получил урон (защитник мертв до контратаки)
            db_session.refresh(battle_unit1)
            assert battle_unit1.remaining_hp == attacker_initial_hp, \
                "Атакующий не должен получить урон (защитник убит до контратаки)"

            # Проверить что в логе нет контратаки
            assert "КОНТРАТАКА" not in message, \
                "Лог не должен содержать информацию о контратаке (защитник мертв)"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
