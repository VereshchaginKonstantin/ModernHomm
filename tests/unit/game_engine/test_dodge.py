#!/usr/bin/env python3
"""
Тесты для механики уклонения (dodge)
"""

import pytest
from decimal import Decimal
import tempfile
import os
from db.models import GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field
from core.game_engine import GameEngine


class TestDodgeSystem:
    """Тесты для системы уклонения"""

    def test_unit_with_zero_dodge_never_dodges(self, db_session):
        """Тест, что юнит с dodge_chance=0 никогда не уклоняется"""
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
            # Создать юнита без уклонения
            unit = Unit(
                name="Warrior",
                icon="⚔️",
                price=Decimal("100"),
                damage=50,
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),  # Нет уклонения
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

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что атака успешна и нанесен урон
            assert success, f"Атака должна быть успешной, но получено: {message}"
            db_session.refresh(battle_unit2)
            assert battle_unit2.remaining_hp < 100, "Цель должна получить урон (уклонения нет)"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_unit_with_perfect_dodge_always_dodges(self, db_session):
        """Тест, что юнит с dodge_chance=1 всегда уклоняется"""
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
                damage=100,  # Большой урон
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                image_path=temp_image_path
            )

            # Создать защищающегося юнита с 100% уклонением
            defender_unit = Unit(
                name="Dodger",
                icon="🌀",
                price=Decimal("100"),
                damage=10,
                defense=0,
                health=50,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("1.0"),  # 100% уклонение
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
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что атака успешна но урон не нанесен (уклонение)
            assert success, f"Атака должна быть успешной, но получено: {message}"
            db_session.refresh(battle_unit2)
            assert battle_unit2.remaining_hp == 50, f"Цель не должна получить урон (уклонение 100%), но HP = {battle_unit2.remaining_hp}"
            assert "УКЛОНЕНИЕ" in message or "уклон" in message.lower(), "Сообщение должно содержать информацию об уклонении"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_dodged_attack_deals_zero_damage(self, db_session):
        """Тест, что при уклонении урон равен 0"""
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
                damage=1000,  # Очень большой урон
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                image_path=temp_image_path
            )

            # Создать защищающегося юнита с 100% уклонением
            defender_unit = Unit(
                name="Dodger",
                icon="🌀",
                price=Decimal("100"),
                damage=10,
                defense=0,
                health=10,  # Малое HP
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("1.0"),  # 100% уклонение
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

            initial_hp = battle_unit2.remaining_hp

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что HP не изменилось
            db_session.refresh(battle_unit2)
            assert battle_unit2.remaining_hp == initial_hp, "HP не должно измениться при уклонении"
            assert battle_unit2.total_count == 1, "Юнит должен остаться жив"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_dodge_log_message(self, db_session):
        """Тест, что лог содержит информацию об уклонении"""
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
            # Создать юнитов
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
                image_path=temp_image_path
            )

            defender_unit = Unit(
                name="Dodger",
                icon="🌀",
                price=Decimal("100"),
                damage=10,
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("1.0"),  # 100% уклонение
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

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что лог содержит информацию об уклонении
            assert "УКЛОНЕНИЕ" in message or "уклонился" in message, f"Лог должен содержать информацию об уклонении, но получено: {message}"
            assert "ИТОГОВЫЙ УРОН: 0" in message, f"Лог должен показывать урон 0, но получено: {message}"
            assert "100.0%" in message, "Лог должен показывать шанс уклонения 100%"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
