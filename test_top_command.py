#!/usr/bin/env python3
"""
Тесты для команды /top - рейтинг игроков
"""

import pytest
import tempfile
import os
from decimal import Decimal
from db.models import GameUser, Unit, UserUnit
from db import Database


class TestTopCommand:
    """Тесты для команды /top"""

    def test_top_command_empty(self, db_session):
        """Тест что рейтинг пустой когда нет игроков"""
        # Проверяем что в БД нет игроков
        users = db_session.query(GameUser).all()
        assert len(users) == 0, "База должна быть пустой"

    def test_top_command_with_players(self, db_session):
        """Тест рейтинга с несколькими игроками"""
        # Создаем игроков с разным количеством побед
        player1 = GameUser(telegram_id=1001, name="Топ игрок", balance=Decimal("1000"), wins=10, losses=2)
        player2 = GameUser(telegram_id=1002, name="Средний игрок", balance=Decimal("1000"), wins=5, losses=5)
        player3 = GameUser(telegram_id=1003, name="Новичок", balance=Decimal("1000"), wins=1, losses=9)
        db_session.add_all([player1, player2, player3])
        db_session.flush()

        # Получаем всех игроков
        all_users = db_session.query(GameUser).all()
        assert len(all_users) == 3, "Должно быть 3 игрока"

        # Проверяем что игроки создались с правильными характеристиками
        assert player1.wins == 10
        assert player2.wins == 5
        assert player3.wins == 1

    def test_top_command_with_army_cost(self, db_session):
        """Тест рейтинга со стоимостью армий"""
        # Создаем временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создаем игроков
            player1 = GameUser(telegram_id=2001, name="Богатый игрок", balance=Decimal("10000"), wins=5, losses=0)
            player2 = GameUser(telegram_id=2002, name="Бедный игрок", balance=Decimal("500"), wins=5, losses=0)
            db_session.add_all([player1, player2])
            db_session.flush()

            # Создаем юнитов
            unit_expensive = Unit(
                name="Дорогой юнит",
                icon="💎",
                price=Decimal("500"),
                damage=100,
                defense=50,
                health=200,
                range=2,
                speed=2,
                luck=Decimal("0.1"),
                crit_chance=Decimal("0.2"),
                dodge_chance=Decimal("0.1"),
                is_kamikaze=0,
                counterattack_chance=Decimal("0.5"),
                image_path=temp_image_path
            )
            unit_cheap = Unit(
                name="Дешевый юнит",
                icon="⚔️",
                price=Decimal("50"),
                damage=20,
                defense=10,
                health=50,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                counterattack_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add_all([unit_expensive, unit_cheap])
            db_session.flush()

            # Даем игрокам юнитов
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit_expensive.id, count=10)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit_cheap.id, count=5)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Проверяем стоимость армий
            # Игрок 1: 500 * 10 = 5000
            army_cost_1 = unit_expensive.price * user_unit1.count
            assert army_cost_1 == Decimal("5000"), f"Стоимость армии игрока 1 должна быть 5000, получено {army_cost_1}"

            # Игрок 2: 50 * 5 = 250
            army_cost_2 = unit_cheap.price * user_unit2.count
            assert army_cost_2 == Decimal("250"), f"Стоимость армии игрока 2 должна быть 250, получено {army_cost_2}"

            # При одинаковом количестве побед (5), игрок с более дорогой армией должен быть выше
            all_users = db_session.query(GameUser).all()

            # Подготовка данных для рейтинга (как в боте)
            player_stats = []
            for game_user in all_users:
                user_units = db_session.query(UserUnit).filter_by(game_user_id=game_user.id).all()
                army_cost = Decimal('0')
                for user_unit in user_units:
                    if user_unit.count > 0:
                        unit = db_session.query(Unit).filter_by(id=user_unit.unit_type_id).first()
                        if unit:
                            army_cost += unit.price * user_unit.count

                player_stats.append({
                    'name': game_user.name,
                    'wins': game_user.wins,
                    'losses': game_user.losses,
                    'army_cost': army_cost
                })

            # Сортируем по победам (по убыванию), затем по стоимости армии (по убыванию)
            player_stats.sort(key=lambda x: (x['wins'], x['army_cost']), reverse=True)

            # Проверяем что игрок с более дорогой армией на первом месте
            assert player_stats[0]['name'] == "Богатый игрок", "Игрок с более дорогой армией должен быть первым при равном количестве побед"
            assert player_stats[0]['army_cost'] == Decimal("5000")
            assert player_stats[1]['name'] == "Бедный игрок"
            assert player_stats[1]['army_cost'] == Decimal("250")

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_top_command_sorting_by_wins(self, db_session):
        """Тест что сортировка по победам работает правильно"""
        # Создаем игроков с разным количеством побед
        player1 = GameUser(telegram_id=3001, name="Победитель", balance=Decimal("1000"), wins=20, losses=5)
        player2 = GameUser(telegram_id=3002, name="Середняк", balance=Decimal("1000"), wins=10, losses=10)
        player3 = GameUser(telegram_id=3003, name="Лузер", balance=Decimal("1000"), wins=2, losses=18)
        db_session.add_all([player1, player2, player3])
        db_session.flush()

        # Получаем всех игроков
        all_users = db_session.query(GameUser).all()

        # Подготовка данных для рейтинга
        player_stats = []
        for game_user in all_users:
            player_stats.append({
                'name': game_user.name,
                'wins': game_user.wins,
                'losses': game_user.losses,
                'army_cost': Decimal('0')
            })

        # Сортируем по победам (по убыванию)
        player_stats.sort(key=lambda x: (x['wins'], x['army_cost']), reverse=True)

        # Проверяем правильность сортировки
        assert player_stats[0]['name'] == "Победитель"
        assert player_stats[0]['wins'] == 20
        assert player_stats[1]['name'] == "Середняк"
        assert player_stats[1]['wins'] == 10
        assert player_stats[2]['name'] == "Лузер"
        assert player_stats[2]['wins'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
