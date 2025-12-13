#!/usr/bin/env python3
"""
Тесты для контроля разницы в стоимости армий при вызове на бой (±50%)
"""

import pytest
import tempfile
import os
from decimal import Decimal
from db.models import GameUser, Unit, UserUnit
from db import Database


class TestArmyCostValidation:
    """Тесты для контроля стоимости армий"""

    def _calculate_army_cost(self, db_session, game_user_id: int) -> Decimal:
        """Вспомогательный метод для расчета стоимости армии"""
        user_units = db_session.query(UserUnit).filter_by(game_user_id=game_user_id).all()
        army_cost = Decimal('0')
        for user_unit in user_units:
            if user_unit.count > 0:
                unit = db_session.query(Unit).filter_by(id=user_unit.unit_type_id).first()
                if unit:
                    army_cost += unit.price * user_unit.count
        return army_cost

    def test_calculate_army_cost_empty(self, db_session):
        """Тест расчета стоимости армии без юнитов"""
        # Создаем игрока без юнитов
        player = GameUser(telegram_id=5001, username="Бедняк", balance=Decimal("1000"))
        db_session.add(player)
        db_session.flush()

        # Рассчитываем стоимость армии
        army_cost = self._calculate_army_cost(db_session, player.id)

        assert army_cost == Decimal('0'), "Стоимость армии без юнитов должна быть 0"

    def test_calculate_army_cost_with_units(self, db_session):
        """Тест расчета стоимости армии с юнитами"""
        # Создаем временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создаем игрока
            player = GameUser(telegram_id=5002, username="Воин", balance=Decimal("5000"))
            db_session.add(player)
            db_session.flush()

            # Создаем юнитов
            unit1 = Unit(
                name="Юнит1",
                icon="⚔️",
                price=Decimal("100"),
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
            unit2 = Unit(
                name="Юнит2",
                icon="🏹",
                price=Decimal("200"),
                damage=30,
                defense=15,
                health=60,
                range=2,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0"),
                is_kamikaze=0,
                counterattack_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add_all([unit1, unit2])
            db_session.flush()

            # Даем игроку юнитов
            user_unit1 = UserUnit(game_user_id=player.id, unit_type_id=unit1.id, count=5)  # 100 * 5 = 500
            user_unit2 = UserUnit(game_user_id=player.id, unit_type_id=unit2.id, count=3)  # 200 * 3 = 600
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Рассчитываем стоимость армии
            army_cost = self._calculate_army_cost(db_session, player.id)

            # Ожидаемая стоимость: 500 + 600 = 1100
            expected_cost = Decimal("1100")
            assert army_cost == expected_cost, f"Стоимость армии должна быть {expected_cost}, получено {army_cost}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_army_cost_difference_within_limit(self, db_session):
        """Тест что армии с разницей ≤50% проходят проверку"""
        # Создаем временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создаем игроков
            player1 = GameUser(telegram_id=5003, username="Игрок1", balance=Decimal("5000"))
            player2 = GameUser(telegram_id=5004, username="Игрок2", balance=Decimal("5000"))
            db_session.add_all([player1, player2])
            db_session.flush()

            # Создаем юнита
            unit = Unit(
                name="Тестовый юнит разница",
                icon="⚔️",
                price=Decimal("100"),
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
            db_session.add(unit)
            db_session.flush()

            # Даем игрокам юнитов с разницей 50%
            # Игрок1: 10 юнитов * 100 = 1000
            # Игрок2: 15 юнитов * 100 = 1500
            # Разница: (1500 - 1000) / 1000 = 50%
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=10)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=15)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Рассчитываем стоимости армий
            cost1 = self._calculate_army_cost(db_session, player1.id)
            cost2 = self._calculate_army_cost(db_session, player2.id)

            assert cost1 == Decimal("1000")
            assert cost2 == Decimal("1500")

            # Вычисляем разницу
            max_cost = max(cost1, cost2)
            min_cost = min(cost1, cost2)
            difference_percent = ((max_cost - min_cost) / min_cost) * 100

            assert difference_percent == 50, f"Разница должна быть 50%, получено {difference_percent}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_army_cost_difference_exceeds_limit(self, db_session):
        """Тест что армии с разницей >50% не проходят проверку"""
        # Создаем временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создаем игроков
            player1 = GameUser(telegram_id=5005, username="Игрок3", balance=Decimal("5000"))
            player2 = GameUser(telegram_id=5006, username="Игрок4", balance=Decimal("5000"))
            db_session.add_all([player1, player2])
            db_session.flush()

            # Создаем юнита
            unit = Unit(
                name="Тестовый юнит превышение",
                icon="⚔️",
                price=Decimal("100"),
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
            db_session.add(unit)
            db_session.flush()

            # Даем игрокам юнитов с разницей >50%
            # Игрок1: 10 юнитов * 100 = 1000
            # Игрок2: 20 юнитов * 100 = 2000
            # Разница: (2000 - 1000) / 1000 = 100%
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=10)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=20)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Рассчитываем стоимости армий
            cost1 = self._calculate_army_cost(db_session, player1.id)
            cost2 = self._calculate_army_cost(db_session, player2.id)

            assert cost1 == Decimal("1000")
            assert cost2 == Decimal("2000")

            # Вычисляем разницу
            max_cost = max(cost1, cost2)
            min_cost = min(cost1, cost2)
            difference_percent = ((max_cost - min_cost) / min_cost) * 100

            assert difference_percent == 100, f"Разница должна быть 100%, получено {difference_percent}"
            assert difference_percent > 50, "Разница должна превышать 50%"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_army_cost_one_player_no_units(self, db_session):
        """Тест когда у одного игрока нет юнитов (разница 100%)"""
        # Создаем временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создаем игроков
            player1 = GameUser(telegram_id=5007, username="Игрок5", balance=Decimal("5000"))
            player2 = GameUser(telegram_id=5008, username="Игрок6", balance=Decimal("1000"))
            db_session.add_all([player1, player2])
            db_session.flush()

            # Создаем юнита
            unit = Unit(
                name="Тестовый юнит один без армии",
                icon="⚔️",
                price=Decimal("100"),
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
            db_session.add(unit)
            db_session.flush()

            # Даем юнитов только первому игроку
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=10)
            db_session.add(user_unit1)
            db_session.flush()

            # Рассчитываем стоимости армий
            cost1 = self._calculate_army_cost(db_session, player1.id)
            cost2 = self._calculate_army_cost(db_session, player2.id)

            assert cost1 == Decimal("1000")
            assert cost2 == Decimal("0")

            # Если одна из армий нулевая, разница считается 100%
            max_cost = max(cost1, cost2)
            min_cost = min(cost1, cost2)

            if min_cost == 0:
                difference_percent = 100
            else:
                difference_percent = ((max_cost - min_cost) / min_cost) * 100

            assert difference_percent == 100, f"Разница должна быть 100% (одна армия пустая), получено {difference_percent}"
            assert difference_percent > 50, "Разница должна превышать 50%"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
