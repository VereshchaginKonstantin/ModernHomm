#!/usr/bin/env python3
"""
Тесты для обновленной формулы расчета стоимости юнитов
"""

import pytest
from decimal import Decimal
from web.app import calculate_unit_price


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

        # Расчет: 100 + 20 + 150 + 2*1*(100+20) + 2*(100+20) + 2*0.1*100 + 2*0.15*100 + 10*0.2*(100+20) + 0
        # = 100 + 20 + 150 + 240 + 240 + 20 + 30 + 240 + 0 = 1040.0
        expected_price = Decimal("1040.00")
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

        # Расчет: 20 + 20 + 150 + 2*1*(20+20) + 2*(20+20) + 2*0.1*20 + 2*0.15*20 + 10*(0.2/50)*(20+20) + 0
        # = 20 + 20 + 150 + 80 + 80 + 4 + 6 + 1.6 + 0 = 361.6
        expected_price = Decimal("361.60")
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

        # Обычный: 50 + 10 + 100 + 2*1*(50+10) + 1*(50+10) + 0 + 0 + 10*0.3*(50+10) + 0 = 520.0
        # Камикадзе: 10 + 10 + 100 + 2*1*(10+10) + 1*(10+10) + 0 + 0 + 10*(0.3/50)*(10+10) + 0 = 181.2
        assert normal_price == Decimal("520.00")
        assert kamikaze_price == Decimal("181.20")

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

        # Без контратаки: 50 + 10 + 100 + 2*1*(50+10) + 1*(50+10) + 0 + 0 + 0 + 0 = 340.0
        # С контратакой 0.5: 50 + 10 + 100 + 2*1*(50+10) + 1*(50+10) + 0 + 0 + 0 + 10*0.5*50 = 590.0
        assert price_without_counter == Decimal("340.00")
        assert price_with_counter == Decimal("590.00")

    def test_price_all_stats_zero(self):
        """Тест стоимости юнита с нулевыми характеристиками"""
        price = calculate_unit_price(
            0, 0, 0, 1, 1,
            0, 0, 0,
            is_kamikaze=0, counterattack_chance=0
        )

        # 0 + 0 + 0 + 2*1*(0+0) + 1*(0+0) + 0 + 0 + 0 + 0 = 0.0
        expected_price = Decimal("0.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"

    def test_price_with_all_max_stats(self):
        """Тест стоимости юнита с максимальными характеристиками"""
        price = calculate_unit_price(
            200, 50, 300, 5, 5,
            1.0, 1.0, 0.9,
            is_kamikaze=0, counterattack_chance=1.0
        )

        # 200 + 50 + 300 + 2*5*(200+50) + 5*(200+50) + 2*1.0*200 + 2*1.0*200 + 10*0.9*(200+50) + 10*1.0*200
        # = 200 + 50 + 300 + 2500 + 1250 + 400 + 400 + 2250 + 2000
        # = 9350.0
        expected_price = Decimal("9350.00")
        assert price == expected_price, f"Ожидаемая цена {expected_price}, получено {price}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
