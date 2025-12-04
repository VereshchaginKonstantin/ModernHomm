#!/usr/bin/env python3
"""
Тесты для снижения стоимости юнитов-камикадзе
"""

import pytest
from decimal import Decimal
from admin_app import calculate_unit_price


class TestKamikazePrice:
    """Тесты для стоимости юнитов-камикадзе"""

    def test_kamikaze_no_dodge_cost(self):
        """Тест, что камикадзе не учитывает уклонение в стоимости"""
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

        # Проверить точное значение
        # Обычная: 100 + 20 + 150 + 100*1 + 100*2 + 1000*0.1 + 1000*0.15 + 1000*0.2 + 0 = 1020.0
        # Камикадзе: 100 + 20 + 150 + 100*1 + 100*2 + 1000*0.1 + 1000*0.15 + 0*0.2 + 0 = 820.0
        assert normal_price == Decimal("1020.00"), f"Обычная цена должна быть 1020.00, получено {normal_price}"
        assert kamikaze_price == Decimal("820.00"), f"Цена камикадзе должна быть 820.00, получено {kamikaze_price}"

        # Проверить что камикадзе дешевле на стоимость уклонения
        dodge_cost = Decimal("200.00")  # 1000 * 0.2
        assert normal_price - kamikaze_price == dodge_cost, "Разница должна быть равна стоимости уклонения"

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

        # Проверить точное значение: 50 + 10 + 100 + 100*2 + 100*1 = 460.0
        expected_price = Decimal("460.00")
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

        # Камикадзе: 200 + 50 + 300 + 100*5 + 100*5 + 1000*1.0 + 1000*1.0 + 0*0.9 + 0 = 3550.0
        expected_price = Decimal("3550.00")
        assert kamikaze_price == expected_price, f"Ожидаемая цена {expected_price}, получено {kamikaze_price}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
