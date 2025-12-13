#!/usr/bin/env python3
"""
Тесты для проверки фиксации убитых юнитов после завершения игры
"""

import pytest
from decimal import Decimal
import tempfile
import os
from db.models import GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field
from core.game_engine import GameEngine


class TestKilledUnitsTracking:
    """Тесты для фиксации убитых юнитов"""

    def test_killed_units_tracked_on_game_completion(self, db_session):
        """Тест, что убитые юниты фиксируются при завершении игры"""
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

            # У первого игрока 3 юнита, у второго 2 юнита
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=3)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=2)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Сохранить начальные количества
            initial_player1_units = user_unit1.count
            initial_player2_units = user_unit2.count

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

            # Создать боевых юнитов (3 юнита у player1, 2 у player2)
            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=3,  # 3 юнита
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

            # Player1 атакует и убивает всех юнитов Player2
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить, что атака успешна и игра завершена
            assert success, f"Атака должна быть успешной, но получено: {message}"
            db_session.refresh(game)
            assert game.status == GameStatus.COMPLETED, "Игра должна быть завершена"
            assert game.winner_id == player1.id, "Player1 должен быть победителем"

            # Получить объекты заново из базы данных
            user_unit1_updated = db_session.query(UserUnit).filter_by(id=user_unit1.id).first()
            user_unit2_updated = db_session.query(UserUnit).filter_by(id=user_unit2.id).first()

            # Проверить, что количество юнитов обновилось
            # У победителя должно остаться 3 юнита (никто не умер)
            assert user_unit1_updated is not None, "Запись UserUnit для победителя должна существовать"
            assert user_unit1_updated.count == 3, f"У победителя должно остаться 3 юнита, но получено: {user_unit1_updated.count}"

            # У проигравшего все юниты должны быть убиты (запись удалена)
            assert user_unit2_updated is None, f"Запись UserUnit для проигравшего должна быть удалена, но count={user_unit2_updated.count if user_unit2_updated else 'N/A'}"

        finally:
            # Удалить временный файл
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_killed_units_tracked_on_surrender(self, db_session):
        """Тест, что убитые юниты фиксируются при сдаче игры"""
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
            # Создать юнита (урон 18, чтобы убить 1-2 юнита из 3)
            # Урон = 18 * 3 атакующих * (0.9-1.1 variance) = 48-59, убьет 0-1 юнита (50 HP)
            unit = Unit(
                name="Warrior",
                icon="⚔️",
                price=Decimal("100"),
                damage=18,
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

            # У обоих игроков по 3 юнита
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=3)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=3)
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

            # Создать боевых юнитов (по 3 юнита)
            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=3,
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
                total_count=3,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            # Player1 атакует и убивает хотя бы 1 юнита Player2
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)
            assert success, "Атака должна быть успешной"

            # Проверить, что у player2 убит хотя бы 1 юнит
            battle_unit2_updated = db_session.query(BattleUnit).filter_by(id=battle_unit2.id).first()
            assert battle_unit2_updated is not None, "BattleUnit для Player2 должен существовать"
            assert battle_unit2_updated.total_count < 3, f"У Player2 должен быть убит хотя бы 1 юнит, но получено: {battle_unit2_updated.total_count}"
            killed_count = 3 - battle_unit2_updated.total_count
            remaining_count = battle_unit2_updated.total_count

            # Player2 сдается
            success, message, opponent_telegram_id = engine.surrender_game(game.id, player2.id)
            assert success, f"Сдача должна быть успешной, но получено: {message}"

            # Получить объекты заново из базы данных
            game_updated = db_session.query(Game).filter_by(id=game.id).first()
            user_unit1_updated = db_session.query(UserUnit).filter_by(id=user_unit1.id).first()
            user_unit2_updated = db_session.query(UserUnit).filter_by(id=user_unit2.id).first()

            # Проверить, что игра завершена
            assert game_updated.status == GameStatus.COMPLETED, "Игра должна быть завершена"
            assert game_updated.winner_id == player1.id, "Player1 должен быть победителем"

            # Проверить, что количество юнитов обновилось
            # У Player1 должно остаться 3 юнита (никто не умер)
            assert user_unit1_updated is not None, "Запись UserUnit для Player1 должна существовать"
            assert user_unit1_updated.count == 3, f"У Player1 должно остаться 3 юнита, но получено: {user_unit1_updated.count}"

            # У Player2 должно остаться столько юнитов, сколько осталось после атаки
            assert user_unit2_updated is not None, "Запись UserUnit для Player2 должна существовать"
            assert user_unit2_updated.count == remaining_count, f"У Player2 должно остаться {remaining_count} юнит(ов) ({killed_count} убито), но получено: {user_unit2_updated.count}"

        finally:
            # Удалить временный файл
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_reward_calculation_based_on_killed_units(self, db_session):
        """Тест, что награда рассчитывается на основе убитых юнитов в игре"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        initial_balance = player1.balance

        # Создать временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создать юнита стоимостью 100
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

            # У Player2 5 юнитов
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
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
                total_count=5,
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
                total_count=5,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            # Player1 атакует и убивает всех юнитов Player2 (5 юнитов)
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            # Проверить, что атака успешна и игра завершена
            assert success, "Атака должна быть успешной"
            db_session.refresh(game)
            assert game.status == GameStatus.COMPLETED, "Игра должна быть завершена"

            # Обновить баланс победителя
            db_session.refresh(player1)

            # Награда должна быть: 5 юнитов * 100 = 500
            expected_reward = Decimal("500")
            expected_balance = initial_balance + expected_reward

            assert player1.balance == expected_balance, \
                f"Баланс победителя должен быть {expected_balance} (начальный {initial_balance} + награда {expected_reward}), но получено: {player1.balance}"

        finally:
            # Удалить временный файл
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
