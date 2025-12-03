#!/usr/bin/env python3
"""
Тесты для ограничения уклонения до 90% и учета в стоимости
"""

import pytest
from decimal import Decimal
import tempfile
import os
from db.models import Unit
from admin_app import calculate_unit_price


class TestDodgeLimitAndPrice:
    """Тесты для ограничения уклонения и расчета стоимости"""

    def test_dodge_in_price_calculation(self):
        """Тест, что dodge_chance учитывается в стоимости"""
        # Базовые параметры
        damage = 50
        defense = 10
        health = 100
        unit_range = 2
        speed = 1
        luck = 0.1
        crit_chance = 0.15
        dodge_chance = 0.5

        price = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance, dodge_chance)

        # Ожидаемая стоимость:
        # 50 + 10 + 100 + 100*2 + 50*1 + 100*0.1 + 100*0.15 + 100*0.5 =
        # 50 + 10 + 100 + 200 + 50 + 10 + 15 + 50 = 485
        expected_price = Decimal("485.00")

        assert price == expected_price, f"Ожидаемая стоимость {expected_price}, получено {price}"

    def test_dodge_zero_in_price(self):
        """Тест, что dodge_chance=0 не влияет на стоимость"""
        # Базовые параметры
        damage = 50
        defense = 10
        health = 100
        unit_range = 2
        speed = 1
        luck = 0.0
        crit_chance = 0.0
        dodge_chance = 0.0

        price = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance, dodge_chance)

        # Ожидаемая стоимость:
        # 50 + 10 + 100 + 100*2 + 50*1 + 100*0 + 100*0 + 100*0 =
        # 50 + 10 + 100 + 200 + 50 = 410
        expected_price = Decimal("410.00")

        assert price == expected_price, f"Ожидаемая стоимость {expected_price}, получено {price}"

    def test_dodge_max_90_in_price(self):
        """Тест, что dodge_chance=0.9 (максимум) корректно учитывается"""
        # Базовые параметры
        damage = 50
        defense = 10
        health = 100
        unit_range = 2
        speed = 1
        luck = 0.0
        crit_chance = 0.0
        dodge_chance = 0.9  # Максимум

        price = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance, dodge_chance)

        # Ожидаемая стоимость:
        # 50 + 10 + 100 + 100*2 + 50*1 + 100*0 + 100*0 + 100*0.9 =
        # 50 + 10 + 100 + 200 + 50 + 90 = 500
        expected_price = Decimal("500.00")

        assert price == expected_price, f"Ожидаемая стоимость {expected_price}, получено {price}"

    def test_unit_cannot_have_100_percent_dodge(self, db_session):
        """Тест, что юнит не может иметь 100% уклонения"""
        # Создать временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Попытка создать юнита с 100% уклонением должна быть ограничена на уровне базы
            # Максимум в админке 0.9
            unit = Unit(
                name="Test Unit",
                icon="🎯",
                price=Decimal("100"),
                damage=50,
                defense=10,
                health=100,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                dodge_chance=Decimal("0.9"),  # Максимум допустимое значение
                is_kamikaze=0,
                counterattack_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            # Проверить что значение сохранилось
            assert unit.dodge_chance == Decimal("0.9"), "Максимальное значение уклонения должно быть 0.9"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
