#!/usr/bin/env python3
"""
Тесты для обновленной формулы расчета стоимости юнитов
"""

import pytest
from decimal import Decimal
from admin_app import calculate_unit_price


class TestPriceFormulaUpdate:
    """Тесты для обновленной формулы стоимости"""

    def test_normal_unit_price_divided_by_20(self):
        """Тест что стоимость обычного юнита делится на 20"""
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

        # Расчет: 100 + 20 + 150 + 100*1 + 50*2 + 10000*0.1 + 10000*0.15 + 10000*0.2 + 10000*0
        # = 100 + 20 + 150 + 100 + 100 + 1000 + 1500 + 2000 + 0 = 4970
        # Делим на 20: 4970 / 20 = 248.5
        expected_price = Decimal("248.50")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_kamikaze_unit_price_divided_by_10_and_20(self):
        """Тест что стоимость камикадзе делится на 10 и на 20"""
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

        # Расчет: 100 + 20 + 150 + 100*1 + 50*2 + 10000*0.1 + 10000*0.15 + 10000*0.2 + 10000*0
        # = 4970
        # Делим на 10 (камикадзе): 4970 / 10 = 497
        # Делим на 20 (всегда): 497 / 20 = 24.85
        expected_price = Decimal("24.85")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_kamikaze_factor_changed_from_5_to_10(self):
        """Тест что фактор камикадзе изменен с 5 на 10"""
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
        # Обычный: 310 / 20 = 15.5
        # Камикадзе: 310 / 10 / 20 = 1.55
        assert normal_price == Decimal("15.50")
        assert kamikaze_price == Decimal("1.55")

        # Проверяем что камикадзе в 10 раз дешевле обычного
        ratio = normal_price / kamikaze_price
        assert ratio == Decimal("10"), f"Соотношение должно быть 10, получено {ratio}"

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

        # Без контратаки: 310 / 20 = 15.5
        # С контратакой 0.5: (310 + 10000*0.5) / 20 = 5310 / 20 = 265.5
        assert price_without_counter == Decimal("15.50")
        assert price_with_counter == Decimal("265.50")

    def test_price_all_stats_zero(self):
        """Тест стоимости юнита с нулевыми характеристиками"""
        price = calculate_unit_price(
            0, 0, 0, 1, 1,
            0, 0, 0,
            is_kamikaze=0, counterattack_chance=0
        )

        # (0 + 0 + 0 + 100*1 + 50*1) / 20 = 150 / 20 = 7.5
        expected_price = Decimal("7.50")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_price_with_all_max_stats(self):
        """Тест стоимости юнита с максимальными характеристиками"""
        price = calculate_unit_price(
            200, 50, 300, 5, 5,
            1.0, 1.0, 0.9,
            is_kamikaze=0, counterattack_chance=1.0
        )

        # (200 + 50 + 300 + 100*5 + 50*5 + 10000*1.0 + 10000*1.0 + 10000*0.9 + 10000*1.0) / 20
        # = (200 + 50 + 300 + 500 + 250 + 10000 + 10000 + 9000 + 10000) / 20
        # = 40300 / 20 = 2015
        expected_price = Decimal("2015.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
