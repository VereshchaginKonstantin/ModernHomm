#!/usr/bin/env python3
"""
Тесты для обновленной формулы расчета стоимости юнитов
"""

import pytest
from decimal import Decimal
from admin_app import calculate_unit_price


class TestPriceFormulaUpdate:
    """Тесты для обновленной формулы стоимости"""

    def test_normal_unit_price_divided_by_10(self):
        """Тест что стоимость обычного юнита делится на 10"""
        damage = 100
        defense = 20
        health = 150
        unit_range = 1
        speed = 2
        luck = 0.1
        crit_chance = 0.15
        dodge_chance = 0.2
        counterattack_chance = 0

        price = calculate_unit_price(
            damage, defense, health, unit_range, speed,
            luck, crit_chance, dodge_chance,
            is_kamikaze=0, counterattack_chance=counterattack_chance
        )

        # Расчет: 100 + 5*20 + 150 + 100*1 + 50*2 + 1000*0.1 + 1000*0.15 + 50000*0.2 + 1000*0
        # = 100 + 100 + 150 + 100 + 100 + 100 + 150 + 10000 + 0 = 10800
        # Делим на 10: 10800 / 10 = 1080.0
        expected_price = Decimal("1080.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_kamikaze_unit_price_divided_by_5_and_10(self):
        """Тест что стоимость камикадзе делится на 5 и на 10"""
        damage = 100
        defense = 20
        health = 150
        unit_range = 1
        speed = 2
        luck = 0.1
        crit_chance = 0.15
        dodge_chance = 0.2
        counterattack_chance = 0

        price = calculate_unit_price(
            damage, defense, health, unit_range, speed,
            luck, crit_chance, dodge_chance,
            is_kamikaze=1, counterattack_chance=counterattack_chance
        )

        # Расчет: 100 + 5*20 + 150 + 100*1 + 50*2 + 1000*0.1 + 1000*0.15 + 50000*0.2 + 1000*0
        # = 10800
        # Делим на 5 (камикадзе): 10800 / 5 = 2160
        # Делим на 10 (всегда): 2160 / 10 = 216.0
        expected_price = Decimal("216.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_kamikaze_factor_is_5(self):
        """Тест что фактор камикадзе равен 5"""
        damage = 50
        defense = 10
        health = 100
        unit_range = 1
        speed = 1
        luck = 0
        crit_chance = 0
        dodge_chance = 0
        counterattack_chance = 0

        normal_price = calculate_unit_price(
            damage, defense, health, unit_range, speed,
            luck, crit_chance, dodge_chance,
            is_kamikaze=0, counterattack_chance=counterattack_chance
        )

        kamikaze_price = calculate_unit_price(
            damage, defense, health, unit_range, speed,
            luck, crit_chance, dodge_chance,
            is_kamikaze=1, counterattack_chance=counterattack_chance
        )

        # Базовая стоимость: 50 + 5*10 + 100 + 100*1 + 50*1 = 350
        # Обычный: 350 / 10 = 35.0
        # Камикадзе: 350 / 5 / 10 = 7.0
        assert normal_price == Decimal("35.00")
        assert kamikaze_price == Decimal("7.00")

        # Проверяем что камикадзе в 5 раз дешевле обычного
        ratio = normal_price / kamikaze_price
        assert ratio == Decimal("5"), f"Соотношение должно быть 5, получено {ratio}"

    def test_price_with_counterattack(self):
        """Тест что контратака учитывается в стоимости"""
        damage = 50
        defense = 10
        health = 100
        unit_range = 1
        speed = 1
        luck = 0
        crit_chance = 0
        dodge_chance = 0

        price_without_counter = calculate_unit_price(
            damage, defense, health, unit_range, speed,
            luck, crit_chance, dodge_chance,
            is_kamikaze=0, counterattack_chance=0
        )

        price_with_counter = calculate_unit_price(
            damage, defense, health, unit_range, speed,
            luck, crit_chance, dodge_chance,
            is_kamikaze=0, counterattack_chance=0.5
        )

        # Без контратаки: 350 / 10 = 35.0
        # С контратакой 0.5: (350 + 1000*0.5) / 10 = 850 / 10 = 85.0
        assert price_without_counter == Decimal("35.00")
        assert price_with_counter == Decimal("85.00")

    def test_price_all_stats_zero(self):
        """Тест стоимости юнита с нулевыми характеристиками"""
        price = calculate_unit_price(
            0, 0, 0, 1, 1,
            0, 0, 0,
            is_kamikaze=0, counterattack_chance=0
        )

        # (0 + 5*0 + 0 + 100*1 + 50*1) / 10 = 150 / 10 = 15.0
        expected_price = Decimal("15.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_price_with_all_max_stats(self):
        """Тест стоимости юнита с максимальными характеристиками"""
        price = calculate_unit_price(
            200, 50, 300, 5, 5,
            1.0, 1.0, 0.9,
            is_kamikaze=0, counterattack_chance=1.0
        )

        # (200 + 5*50 + 300 + 100*5 + 50*5 + 1000*1.0 + 1000*1.0 + 50000*0.9 + 1000*1.0) / 10
        # = (200 + 250 + 300 + 500 + 250 + 1000 + 1000 + 45000 + 1000) / 10
        # = 49500 / 10 = 4950.0
        expected_price = Decimal("4950.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
