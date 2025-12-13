#!/usr/bin/env python3
"""
Тесты для механики камикадзе (is_kamikaze)
"""

import pytest
from decimal import Decimal
import tempfile
import os
from db.models import GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field
from core.game_engine import GameEngine


class TestKamikazeSystem:
    """Тесты для системы камикадзе"""

    def test_kamikaze_unit_uses_single_unit_damage(self, db_session):
        """Тест, что камикадзе юнит наносит урон как 1 юнит (без множителя)"""
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
            # Создать камикадзе юнита с небольшим уроном
            kamikaze_unit = Unit(
                name="Kamikaze",
                icon="💣",
                price=Decimal("100"),
                damage=10,  # Малый урон для легкого тестирования
                defense=0,
                health=50,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=1,  # Камикадзе
                image_path=temp_image_path
            )

            # Создать обычного юнита
            normal_unit = Unit(
                name="Defender",
                icon="🛡️",
                price=Decimal("100"),
                damage=10,
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                image_path=temp_image_path
            )
            db_session.add_all([kamikaze_unit, normal_unit])
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=kamikaze_unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=normal_unit.id, count=1)
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
                total_count=5,  # 5 камикадзе юнитов
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
                remaining_hp=100,
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

            # Проверить что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить что урон рассчитан за 1 юнита (не за 5)
            db_session.refresh(battle_unit2)
            damage_dealt = initial_hp - battle_unit2.remaining_hp

            # Урон должен быть примерно 10 (за 1 юнита), а не ~50 (за 5 юнитов)
            # Учитываем случайность ±10%: урон от 9 до 11
            assert damage_dealt >= 9 and damage_dealt <= 11, \
                f"Камикадзе должен наносить урон за 1 юнита (~10), но нанесено {damage_dealt}"

            # Проверить что в логе упоминается камикадзе
            assert "КАМИКАДЗЕ" in message or "камикадзе" in message.lower(), \
                "Лог должен содержать информацию о камикадзе"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_kamikaze_unit_loses_one_after_attack(self, db_session):
        """Тест, что камикадзе юнит теряет 1 юнита после атаки"""
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
            # Создать камикадзе юнита
            kamikaze_unit = Unit(
                name="Kamikaze",
                icon="💣",
                price=Decimal("100"),
                damage=50,
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=1,
                image_path=temp_image_path
            )

            # Создать целевого юнита
            target_unit = Unit(
                name="Target",
                icon="🎯",
                price=Decimal("100"),
                damage=10,
                defense=0,
                health=200,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                image_path=temp_image_path
            )
            db_session.add_all([kamikaze_unit, target_unit])
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=kamikaze_unit.id, count=3)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=target_unit.id, count=1)
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
                total_count=3,
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

            initial_count = battle_unit1.total_count

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить что количество камикадзе юнитов уменьшилось на 1
            db_session.refresh(battle_unit1)
            assert battle_unit1.total_count == initial_count - 1, \
                f"Камикадзе должен потерять 1 юнита (было {initial_count}, стало {battle_unit1.total_count})"

            # Проверить что в логе упоминается потеря юнита
            assert "потерял 1 юнита" in message or "осталось:" in message, \
                "Лог должен содержать информацию о потере камикадзе юнита"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_kamikaze_unit_dies_when_count_reaches_zero(self, db_session):
        """Тест, что камикадзе юнит удаляется с поля когда счетчик достигает 0"""
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
            # Создать камикадзе юнита с 1 юнитом
            kamikaze_unit = Unit(
                name="Kamikaze",
                icon="💣",
                price=Decimal("100"),
                damage=50,
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=1,
                image_path=temp_image_path
            )

            # Создать целевого юнита
            target_unit = Unit(
                name="Target",
                icon="🎯",
                price=Decimal("100"),
                damage=10,
                defense=0,
                health=200,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                image_path=temp_image_path
            )
            db_session.add_all([kamikaze_unit, target_unit])
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=kamikaze_unit.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=target_unit.id, count=1)
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

            # Создать боевых юнитов - только 1 камикадзе
            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=1,  # Только 1 юнит
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

            kamikaze_id = battle_unit1.id

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить что камикадзе юнит удален из базы
            deleted_unit = db_session.query(BattleUnit).filter_by(id=kamikaze_id).first()
            assert deleted_unit is None, "Камикадзе юнит должен быть удален после атаки с последним юнитом"

            # Проверить что в логе упоминается смерть всех камикадзе
            assert "погибли" in message.lower() or "осталось: 0" in message, \
                "Лог должен содержать информацию о смерти всех камикадзе юнитов"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_non_kamikaze_unit_keeps_full_multiplier(self, db_session):
        """Тест, что обычный (не камикадзе) юнит использует полный множитель"""
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
            # Создать обычного юнита с малым уроном
            normal_unit = Unit(
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
                dodge_chance=Decimal("0"),
                is_kamikaze=0,  # НЕ камикадзе
                image_path=temp_image_path
            )

            # Создать целевого юнита
            target_unit = Unit(
                name="Target",
                icon="🎯",
                price=Decimal("100"),
                damage=10,
                defense=0,
                health=200,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                image_path=temp_image_path
            )
            db_session.add_all([normal_unit, target_unit])
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=normal_unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=target_unit.id, count=1)
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
                total_count=5,  # 5 обычных юнитов
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

            initial_hp = battle_unit2.remaining_hp
            initial_count = battle_unit1.total_count

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить что урон рассчитан за все 5 юнитов
            db_session.refresh(battle_unit2)
            damage_dealt = initial_hp - battle_unit2.remaining_hp

            # Урон должен быть примерно 50 (10 * 5), а не 10 (за 1)
            # Учитываем случайность ±10%: урон от 45 до 55
            assert damage_dealt >= 45 and damage_dealt <= 55, \
                f"Обычный юнит должен наносить урон за всех юнитов (~50), но нанесено {damage_dealt}"

            # Проверить что количество обычных юнитов НЕ изменилось
            db_session.refresh(battle_unit1)
            assert battle_unit1.total_count == initial_count, \
                f"Обычный юнит НЕ должен терять юнитов после атаки"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
