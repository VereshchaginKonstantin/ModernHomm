#!/usr/bin/env python3
"""
Тесты для функциональности бота
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from db import Database
from db.models import GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field
from bot.main import SimpleBot
from core.game_engine import GameEngine


class TestBotGameResults:
    """Тесты для вывода результатов игры"""

    def test_build_game_result_message(self, db_session):
        """Тест форматирования сообщения с результатами игры"""
        # Создать тестовых пользователей
        player1 = GameUser(
            telegram_id=111,
            name="Player1",
            balance=Decimal("1500.00"),
            wins=5,
            losses=3
        )
        player2 = GameUser(
            telegram_id=222,
            name="Player2",
            balance=Decimal("1000.00"),
            wins=2,
            losses=6
        )
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать игру
        field = Field(name="5x5", width=5, height=5)
        db_session.add(field)
        db_session.flush()

        game = Game(
            player1_id=player1.id,
            player2_id=player2.id,
            field_id=field.id,
            status=GameStatus.COMPLETED,
            winner_id=player1.id,
            started_at=datetime.utcnow() - timedelta(minutes=15),
            completed_at=datetime.utcnow()
        )
        db_session.add(game)
        db_session.flush()

        # Создать бота (для доступа к методу _build_game_result_message)
        bot = SimpleBot(db=Database(None))

        # Вызвать метод форматирования результатов
        result_message = bot._build_game_result_message(game, player1, player2, "Test attack message")

        # Проверки
        assert "ИГРА ЗАВЕРШЕНА" in result_message
        assert "Test attack message" in result_message
        assert "Player1" in result_message
        assert "Player2" in result_message
        assert "Победитель" in result_message
        assert "Проигравший" in result_message
        assert "$1500" in result_message  # Баланс победителя
        assert "Побед: 5" in result_message  # Статистика победителя
        assert "Длительность игры" in result_message


class TestGameEngine:
    """Тесты для игрового движка"""

    def test_game_completion_on_all_units_dead(self, db_session):
        """Тест завершения игры при уничтожении всех юнитов противника"""
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
            damage=100,
            defense=0,
            health=10,
            range=1,
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

        # Создать боевых юнитов
        battle_unit1 = BattleUnit(
            game_id=game.id,
            user_unit_id=user_unit1.id,
            player_id=player1.id,
            position_x=0,
            position_y=0,
            total_count=1,
            remaining_hp=10,
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
            remaining_hp=10,
            morale=0,
            fatigue=0,
            has_moved=0
        )
        db_session.add_all([battle_unit1, battle_unit2])
        db_session.flush()

        # Создать движок и выполнить атаку
        engine = GameEngine(db_session)
        success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

        # Проверки
        assert success, "Атака должна быть успешной"
        db_session.refresh(game)
        assert game.status == GameStatus.COMPLETED, "Игра должна быть завершена"
        assert game.winner_id == player1.id, "Player1 должен быть победителем"
        assert "Игра окончена" in message or "победитель" in message.lower(), "Сообщение должно содержать информацию о победе"


class TestGameResultsCleanup:
    """Тесты для проверки очистки поля и кнопок после завершения игры"""

    def test_game_over_removes_dead_units(self, db_session):
        """Тест удаления мертвых юнитов после завершения игры"""
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
            damage=100,
            defense=0,
            health=10,
            range=1,
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

        # Создать боевых юнитов
        battle_unit1 = BattleUnit(
            game_id=game.id,
            user_unit_id=user_unit1.id,
            player_id=player1.id,
            position_x=0,
            position_y=0,
            total_count=1,
            remaining_hp=10,
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
            remaining_hp=10,
            morale=0,
            fatigue=0,
            has_moved=0
        )
        db_session.add_all([battle_unit1, battle_unit2])
        db_session.flush()

        # Выполнить атаку, которая убьет второго юнита
        engine = GameEngine(db_session)
        success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

        # Проверить, что игра завершена
        db_session.refresh(game)
        assert game.status == GameStatus.COMPLETED, "Игра должна быть завершена"
        assert game.winner_id == player1.id, "Player1 должен быть победителем"

        # Проверить, что убитый юнит удален из battle_units
        remaining_battle_units = db_session.query(BattleUnit).filter_by(game_id=game.id).all()
        alive_units = [bu for bu in remaining_battle_units if bu.total_count > 0]

        # После завершения игры, должен остаться только один живой юнит
        assert len(alive_units) == 1, f"Должен остаться только один живой юнит, но найдено {len(alive_units)}"
        assert alive_units[0].player_id == player1.id, "Должен остаться юнит победителя"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
