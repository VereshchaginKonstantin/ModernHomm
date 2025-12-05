#!/usr/bin/env python3
"""
Тесты для обновленной формулы расчета стоимости юнитов
"""

import pytest
from decimal import Decimal
from admin_app import calculate_unit_price


class TestPriceFormulaUpdate:
    """Тесты для обновленной формулы стоимости"""

    def test_normal_unit_price(self):
        """Тест расчета стоимости обычного юнита по новой формуле"""
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

        # Расчет: 100 + 20 + 150 + 100*1 + 100*2 + 1000*0.1 + 1000*0.15 + 5000*0.2 + 1000*0
        # = 100 + 20 + 150 + 100 + 200 + 100 + 150 + 1000 + 0 = 1820.0
        expected_price = Decimal("1820.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_kamikaze_unit_price_without_dodge(self):
        """Тест что стоимость камикадзе не учитывает уклонение"""
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

        # Расчет: 100/5 + 20 + 150 + 100*1 + 100*2 + 1000*0.1 + 1000*0.15 + 100*0.2 + 1000*0
        # = 20 + 20 + 150 + 100 + 200 + 100 + 150 + 20 + 0 = 760.0
        expected_price = Decimal("760.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_kamikaze_vs_normal_with_dodge(self):
        """Тест что камикадзе дешевле обычного когда есть уклонение"""
        damage = 50
        defense = 10
        health = 100
        unit_range = 1
        speed = 1
        luck = 0
        crit_chance = 0
        dodge_chance = 0.3  # Значимое уклонение
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

        # Обычный: 50 + 10 + 100 + 100*1 + 100*1 + 0 + 0 + 5000*0.3 + 0 = 1860.0
        # Камикадзе: 50/5 + 10 + 100 + 100*1 + 100*1 + 0 + 0 + 100*0.3 + 0 = 350.0
        assert normal_price == Decimal("1860.00")
        assert kamikaze_price == Decimal("350.00")

        # Проверяем что камикадзе дешевле из-за отсутствия уклонения в цене
        assert kamikaze_price < normal_price, "Камикадзе должен быть дешевле обычного юнита с уклонением"

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

        # Без контратаки: 50 + 10 + 100 + 100*1 + 100*1 = 360.0
        # С контратакой 0.5: 360 + 1000*0.5 = 860.0
        assert price_without_counter == Decimal("360.00")
        assert price_with_counter == Decimal("860.00")

    def test_price_all_stats_zero(self):
        """Тест стоимости юнита с нулевыми характеристиками"""
        price = calculate_unit_price(
            0, 0, 0, 1, 1,
            0, 0, 0,
            is_kamikaze=0, counterattack_chance=0
        )

        # 0 + 0 + 0 + 100*1 + 100*1 + 0 + 0 + 0 + 0 = 200.0
        expected_price = Decimal("200.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_price_with_all_max_stats(self):
        """Тест стоимости юнита с максимальными характеристиками"""
        price = calculate_unit_price(
            200, 50, 300, 5, 5,
            1.0, 1.0, 0.9,
            is_kamikaze=0, counterattack_chance=1.0
        )

        # 200 + 50 + 300 + 100*5 + 100*5 + 1000*1.0 + 1000*1.0 + 5000*0.9 + 1000*1.0
        # = 200 + 50 + 300 + 500 + 500 + 1000 + 1000 + 4500 + 1000
        # = 9050.0
        expected_price = Decimal("9050.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
