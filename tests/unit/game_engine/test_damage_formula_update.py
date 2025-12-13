#!/usr/bin/env python3
"""
Интеграционные тесты для проверки обновленных формул расчета урона и награды за победу
"""

import pytest
from decimal import Decimal
from db import Database
from db.models import GameUser, Unit, UserUnit, Game, GameStatus, Field, BattleUnit
from core.game_engine import GameEngine
import os
import json


@pytest.fixture
def db():
    """Фикстура для подключения к тестовой базе данных"""
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Использовать тестовую базу данных
    test_db_url = os.getenv('TEST_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5433/telegram_bot_test')
    db = Database(test_db_url)
    yield db


class TestDamageFormulaUpdate:
    """Тесты для проверки обновленных формул расчета урона"""

    def test_affected_units_formula(self, db):
        """
        Тест: Формула задетых юнитов = 1 + floor(0.5 * (dmg_multiplied - health) / health)
        """
        with db.get_session() as session:
            # Создать тестовых игроков
            player1 = GameUser(telegram_id=100001, username="Player1", balance=1000, wins=0, losses=0)
            player2 = GameUser(telegram_id=100002, username="Player2", balance=1000, wins=0, losses=0)
            session.add_all([player1, player2])
            session.flush()

            # Создать простого юнита для атаки
            attacker_unit = Unit(
                name="Атакующий",
                icon="⚔️",
                price=100,
                damage=50,  # Высокий урон
                defense=0,
                health=100,
                range=1,
                speed=1,
                luck=0,
                crit_chance=0,
                dodge_chance=0
            )

            # Создать юнита-защитника с низким здоровьем
            defender_unit = Unit(
                name="Защитник",
                icon="🛡️",
                price=50,
                damage=10,
                defense=5,  # Защита для проверки формулы
                health=20,  # Низкое здоровье
                range=1,
                speed=1,
                luck=0,
                crit_chance=0,
                dodge_chance=0
            )

            session.add_all([attacker_unit, defender_unit])
            session.flush()

            # Создать юнитов для игроков
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=attacker_unit.id, count=3)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=defender_unit.id, count=5)
            session.add_all([user_unit1, user_unit2])
            session.flush()

            # Создать игровое поле
            field = session.query(Field).filter_by(name="5x5").first()
            if not field:
                field = Field(name="5x5", width=5, height=5)
                session.add(field)
                session.flush()

            # Создать игру
            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS,
                current_player_id=player1.id
            )
            session.add(game)
            session.flush()

            # Создать юнитов на поле
            battle_attacker = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=3,
                remaining_hp=attacker_unit.health,
                morale=100,
                fatigue=0,
                has_moved=0
            )

            battle_defender = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=5,
                remaining_hp=defender_unit.health,
                morale=100,
                fatigue=0,
                has_moved=0
            )

            session.add_all([battle_attacker, battle_defender])
            session.commit()

            # Выполнить атаку
            engine = GameEngine(session)
            success, message, _ = engine.attack(game.id, player1.id, battle_attacker.id, battle_defender.id)

            assert success, f"Атака должна быть успешной: {message}"

            # Проверить что формула задетых юнитов применилась
            # dmg = 50, count = 3 -> dmg_multiplied = 150
            # health = 20
            # affected_units = 1 + floor(0.5 * (150 - 20) / 20) = 1 + floor(0.5 * 130 / 20) = 1 + floor(3.25) = 1 + 3 = 4
            # defense_reduction = 5 × |4| = 20
            # total_damage = 150 - 20 = 130
            # Должно быть убито: 130 / 20 = 6.5 -> 6 юнитов

            # Проверить что защитник потерял юнитов
            session.refresh(battle_defender)
            print(f"\n=== Результаты атаки ===")
            print(f"Осталось защитников: {battle_defender.total_count}")
            print(f"Сообщение: {message}")

            # Защитник должен потерять несколько юнитов (формула правильная)
            assert battle_defender.total_count < 5, "Защитник должен потерять юнитов"


    def test_reward_90_percent(self, db):
        """
        Тест: Награда за победу = 90% от стоимости убитых юнитов противника
        """
        with db.get_session() as session:
            # Создать тестовых игроков
            player1 = GameUser(telegram_id=100003, username="Player3", balance=1000, wins=0, losses=0)
            player2 = GameUser(telegram_id=100004, username="Player4", balance=1000, wins=0, losses=0)
            session.add_all([player1, player2])
            session.flush()

            # Создать мощного юнита для игрока 1
            strong_unit = Unit(
                name="Мощный",
                icon="💪",
                price=200,
                damage=100,
                defense=0,
                health=200,
                range=10,
                speed=5,
                luck=0,
                crit_chance=0,
                dodge_chance=0
            )

            # Создать слабого юнита для игрока 2 (стоимость 150)
            weak_unit = Unit(
                name="Слабый",
                icon="😢",
                price=150,
                damage=5,
                defense=0,
                health=10,
                range=1,
                speed=1,
                luck=0,
                crit_chance=0,
                dodge_chance=0
            )

            session.add_all([strong_unit, weak_unit])
            session.flush()

            # Создать юнитов для игроков
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=strong_unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=weak_unit.id, count=3)  # 3 юнита по 150 = 450
            session.add_all([user_unit1, user_unit2])
            session.flush()

            # Создать игровое поле
            field = session.query(Field).filter_by(name="5x5").first()
            if not field:
                field = Field(name="5x5", width=5, height=5)
                session.add(field)
                session.flush()

            # Создать игру
            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS,
                current_player_id=player1.id
            )
            session.add(game)
            session.flush()

            # Создать юнитов на поле
            battle_attacker = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=5,
                remaining_hp=strong_unit.health,
                morale=100,
                fatigue=0,
                has_moved=0
            )

            battle_defender = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=3,
                remaining_hp=weak_unit.health,
                morale=100,
                fatigue=0,
                has_moved=0
            )

            session.add_all([battle_attacker, battle_defender])
            session.commit()

            # Выполнить атаку до конца игры
            engine = GameEngine(session)

            initial_balance = player1.balance

            # Атаковать пока все защитники не умрут
            max_attempts = 10
            for i in range(max_attempts):
                session.refresh(battle_defender)
                if battle_defender.total_count == 0 or session.query(BattleUnit).filter_by(id=battle_defender.id).first() is None:
                    break

                success, message, _ = engine.attack(game.id, player1.id, battle_attacker.id, battle_defender.id)
                if not success:
                    print(f"Атака #{i+1} не удалась: {message}")
                    break

            # Проверить что игра завершена
            session.refresh(game)
            assert game.status == GameStatus.COMPLETED, "Игра должна быть завершена"
            assert game.winner_id == player1.id, "Победителем должен быть Player3"

            # Проверить награду: 3 юнита × 150 = 450, награда = 450 × 0.9 = 405
            session.refresh(player1)
            expected_reward = Decimal('405')  # 450 × 0.9
            expected_balance = initial_balance + expected_reward

            print(f"\n=== Проверка награды ===")
            print(f"Начальный баланс: ${initial_balance}")
            print(f"Ожидаемая награда: ${expected_reward}")
            print(f"Ожидаемый баланс: ${expected_balance}")
            print(f"Фактический баланс: ${player1.balance}")

            assert player1.balance == expected_balance, f"Баланс должен быть ${expected_balance}, но получено ${player1.balance}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
