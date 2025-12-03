#!/usr/bin/env python3
"""
Тесты для снижения стоимости юнитов-камикадзе
"""

import pytest
from decimal import Decimal
from admin_app import calculate_unit_price


class TestKamikazePrice:
    """Тесты для стоимости юнитов-камикадзе"""

    def test_kamikaze_reduces_price_by_5(self):
        """Тест, что камикадзе снижает стоимость в 5 раз"""
        # Базовые параметры
        damage = 100
        defense = 20
        health = 150
        unit_range = 1
        speed = 2
        luck = 0.1
        crit_chance = 0.15
        dodge_chance = 0.2

        # Рассчитать цену обычного юнита
        normal_price = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance, dodge_chance, is_kamikaze=0, counterattack_chance=0)

        # Рассчитать цену юнита-камикадзе
        kamikaze_price = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance, dodge_chance, is_kamikaze=1, counterattack_chance=0)

        # Проверить, что цена камикадзе в 5 раз меньше
        expected_kamikaze_price = normal_price / 5
        assert kamikaze_price == expected_kamikaze_price, f"Ожидаемая цена камикадзе {expected_kamikaze_price}, получено {kamikaze_price}"

        # Проверить точное значение
        # Обычная цена: 100 + 20 + 150 + 100*1 + 50*2 + 10000*0.1 + 10000*0.15 + 10000*0.2 + 10000*0
        #            = 100 + 20 + 150 + 100 + 100 + 1000 + 1500 + 2000 + 0 = 4970
        # Камикадзе: 4970 / 5 = 994
        assert normal_price == Decimal("4970.00"), f"Обычная цена должна быть 4970, получено {normal_price}"
        assert kamikaze_price == Decimal("994.00"), f"Цена камикадзе должна быть 994, получено {kamikaze_price}"

    def test_non_kamikaze_price_unchanged(self):
        """Тест, что обычный юнит (не камикадзе) имеет нормальную цену"""
        damage = 50
        defense = 10
        health = 100
        unit_range = 2
        speed = 1
        luck = 0.0
        crit_chance = 0.0
        dodge_chance = 0.0

        # Без is_kamikaze (по умолчанию 0)
        price1 = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance, dodge_chance)

        # С явным is_kamikaze=0
        price2 = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance, dodge_chance, is_kamikaze=0, counterattack_chance=0)

        # Проверить что цены одинаковые
        assert price1 == price2, "Цены должны быть одинаковыми для не-камикадзе"

        # Проверить точное значение: 50 + 10 + 100 + 100*2 + 50*1 + 10000*0 + 10000*0 + 10000*0 + 10000*0 = 410
        expected_price = Decimal("410.00")
        assert price1 == expected_price, f"Ожидаемая цена {expected_price}, получено {price1}"

    def test_kamikaze_with_max_stats(self):
        """Тест цены камикадзе с максимальными характеристиками"""
        damage = 200
        defense = 50
        health = 300
        unit_range = 5
        speed = 5
        luck = 1.0
        crit_chance = 1.0
        dodge_chance = 0.9

        kamikaze_price = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance, dodge_chance, is_kamikaze=1, counterattack_chance=0)

        # Обычная цена: 200 + 50 + 300 + 100*5 + 50*5 + 10000*1.0 + 10000*1.0 + 10000*0.9 + 10000*0 = 200 + 50 + 300 + 500 + 250 + 10000 + 10000 + 9000 + 0 = 30300
        # Камикадзе: 30300 / 5 = 6060
        expected_price = Decimal("6060.00")
        assert kamikaze_price == expected_price, f"Ожидаемая цена {expected_price}, получено {kamikaze_price}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
