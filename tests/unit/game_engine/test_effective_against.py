#!/usr/bin/env python3
"""
Тесты для эффективности юнитов против определенных типов (x1.5 урона)
"""

import pytest
from decimal import Decimal
import tempfile
import os
from db.models import GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field
from core.game_engine import GameEngine


class TestEffectiveAgainst:
    """Тесты для эффективности юнитов"""

    def test_unit_effective_against_deals_bonus_damage(self, db_session):
        """Тест, что юнит наносит x1.5 урона против эффективного типа"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать временные файлы для изображений
        temp_files = []
        for _ in range(2):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
                temp_files.append(f.name)
                f.write("test image data")

        try:
            # Создать два типа юнитов: Рыцарь (эффективен против Дракона) и Дракон
            dragon = Unit(
                name="Dragon",
                icon="🐉",
                price=Decimal("200"),
                damage=50,
                defense=10,
                health=200,
                range=2,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_files[0]
            )
            db_session.add(dragon)
            db_session.flush()

            knight = Unit(
                name="Knight",
                icon="🛡️",
                price=Decimal("150"),
                damage=40,
                defense=5,
                health=150,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_files[1],
                effective_against_unit_id=dragon.id  # Рыцарь эффективен против Дракона
            )
            db_session.add(knight)
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=knight.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=dragon.id, count=1)
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
            battle_unit_knight = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=1,
                remaining_hp=150,
                morale=0,
                fatigue=0,
                has_moved=0
            )
            battle_unit_dragon = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=1,
                remaining_hp=200,
                morale=0,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit_knight, battle_unit_dragon])
            db_session.flush()

            # Выполнить атаку Рыцаря на Дракона
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit_knight.id, battle_unit_dragon.id)

            # Проверить, что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить, что в сообщении упоминается эффективность
            assert "ЭФФЕКТИВНОСТЬ" in message or "эффективен" in message.lower(), \
                f"Сообщение должно содержать информацию об эффективности, но получено: {message}"

            # Проверить, что урон был увеличен
            # Базовый урон: 40, с учетом эффективности x1.5 = 60
            # С учетом случайности (±10%) и защиты (10), урон должен быть в районе 44-56
            initial_hp = 200
            db_session.refresh(battle_unit_dragon)
            damage_dealt = initial_hp - battle_unit_dragon.remaining_hp

            # Урон должен быть больше, чем базовый урон минус защита (40 - 10 = 30)
            # С учетом эффективности и минимальной случайности: (40 * 0.9 * 1.5) - 10 = 44
            assert damage_dealt >= 40, f"Урон должен быть >= 40 с учетом эффективности, но получено: {damage_dealt}"

        finally:
            # Удалить временные файлы
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

    def test_unit_without_effectiveness_deals_normal_damage(self, db_session):
        """Тест, что юнит без эффективности наносит обычный урон"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать временные файлы для изображений
        temp_files = []
        for _ in range(2):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
                temp_files.append(f.name)
                f.write("test image data")

        try:
            # Создать два типа юнитов без эффективности
            warrior1 = Unit(
                name="Warrior1",
                icon="⚔️",
                price=Decimal("100"),
                damage=40,
                defense=5,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_files[0],
                effective_against_unit_id=None  # Нет эффективности
            )
            warrior2 = Unit(
                name="Warrior2",
                icon="🗡️",
                price=Decimal("100"),
                damage=40,
                defense=5,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_files[1]
            )
            db_session.add_all([warrior1, warrior2])
            db_session.flush()

            # Создать юнитов игрокам
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=warrior1.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=warrior2.id, count=1)
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
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            # Выполнить атаку
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить, что атака успешна
            assert success, f"Атака должна быть успешной, но получено: {message}"

            # Проверить, что в сообщении НЕТ информации об эффективности
            assert "ЭФФЕКТИВНОСТЬ" not in message and "эффективен" not in message.lower(), \
                f"Сообщение НЕ должно содержать информацию об эффективности, но получено: {message}"

            # Проверить, что урон обычный
            # Базовый урон: 40, с учетом защиты (5) и случайности (±10%): 27-40
            initial_hp = 100
            db_session.refresh(battle_unit2)
            damage_dealt = initial_hp - battle_unit2.remaining_hp

            assert 25 <= damage_dealt <= 42, f"Урон должен быть в пределах 25-42 (обычный урон), но получено: {damage_dealt}"

        finally:
            # Удалить временные файлы
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
