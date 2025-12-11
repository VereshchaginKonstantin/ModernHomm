#!/usr/bin/env python3
"""
Тесты для снижения стоимости юнитов-камикадзе
"""

import pytest
from decimal import Decimal
from web_interface import calculate_unit_price


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
        # Обычная: 100 + 20 + 150 + 2*1*(100+20) + 2*(100+20) + 2*0.1*100 + 2*0.15*100 + 10*0.2*(100+20) + 0 = 1040.0
        # Камикадзе: 20 + 20 + 150 + 2*1*(20+20) + 2*(20+20) + 2*0.1*20 + 2*0.15*20 + 10*(0.2/50)*(20+20) + 0 = 361.6
        assert normal_price == Decimal("1040.00"), f"Обычная цена должна быть 1040.00, получено {normal_price}"
        assert kamikaze_price == Decimal("361.60"), f"Цена камикадзе должна быть 361.60, получено {kamikaze_price}"

        # Проверить что камикадзе дешевле (учитывается снижение урона и уклонения)
        price_difference = Decimal("678.40")
        assert normal_price - kamikaze_price == price_difference, f"Разница должна быть {price_difference}"

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

        # Проверить точное значение: 50 + 10 + 100 + 2*2*(50+10) + 1*(50+10) + 0 + 0 + 0 + 0 = 460.0
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

        # Камикадзе: 40 + 50 + 300 + 2*5*(40+50) + 5*(40+50) + 2*1.0*40 + 2*1.0*40 + 10*(0.9/50)*(40+50) + 0 = 1916.2
        expected_price = Decimal("1916.20")
        assert kamikaze_price == expected_price, f"Ожидаемая цена {expected_price}, получено {kamikaze_price}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
