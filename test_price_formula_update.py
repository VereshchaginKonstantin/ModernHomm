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

        # Расчет: 100 + 20 + 150 + 100*1 + 50*2 + 1000*0.1 + 1000*0.15 + 1000*0.2 + 1000*0
        # = 100 + 20 + 150 + 100 + 100 + 100 + 150 + 200 + 0 = 920
        # Делим на 10: 920 / 10 = 92.0
        expected_price = Decimal("92.00")
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

        # Расчет: 100 + 20 + 150 + 100*1 + 50*2 + 1000*0.1 + 1000*0.15 + 1000*0.2 + 1000*0
        # = 920
        # Делим на 5 (камикадзе): 920 / 5 = 184
        # Делим на 10 (всегда): 184 / 10 = 18.4
        expected_price = Decimal("18.40")
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

        # Базовая стоимость: 50 + 10 + 100 + 100*1 + 50*1 = 310
        # Обычный: 310 / 10 = 31.0
        # Камикадзе: 310 / 5 / 10 = 6.2
        assert normal_price == Decimal("31.00")
        assert kamikaze_price == Decimal("6.20")

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

        # Без контратаки: 310 / 10 = 31.0
        # С контратакой 0.5: (310 + 1000*0.5) / 10 = 810 / 10 = 81.0
        assert price_without_counter == Decimal("31.00")
        assert price_with_counter == Decimal("81.00")

    def test_price_all_stats_zero(self):
        """Тест стоимости юнита с нулевыми характеристиками"""
        price = calculate_unit_price(
            0, 0, 0, 1, 1,
            0, 0, 0,
            is_kamikaze=0, counterattack_chance=0
        )

        # (0 + 0 + 0 + 100*1 + 50*1) / 10 = 150 / 10 = 15.0
        expected_price = Decimal("15.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_price_with_all_max_stats(self):
        """Тест стоимости юнита с максимальными характеристиками"""
        price = calculate_unit_price(
            200, 50, 300, 5, 5,
            1.0, 1.0, 0.9,
            is_kamikaze=0, counterattack_chance=1.0
        )

        # (200 + 50 + 300 + 100*5 + 50*5 + 1000*1.0 + 1000*1.0 + 1000*0.9 + 1000*1.0) / 10
        # = (200 + 50 + 300 + 500 + 250 + 1000 + 1000 + 900 + 1000) / 10
        # = 5200 / 10 = 520.0
        expected_price = Decimal("520.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
