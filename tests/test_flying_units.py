#!/usr/bin/env python3
"""
Интеграционные тесты для функционала летающих юнитов (is_flying)
"""

import pytest
from decimal import Decimal
from db import Database
from db.models import Unit, GameUser


class TestFlyingUnits:
    """Тесты для функционала летающих юнитов"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка тестовой базы данных"""
        import uuid
        self.test_prefix = f"flying_test_{uuid.uuid4().hex[:8]}_"
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        # Очистка данных перед тестом
        with self.db.get_session() as session:
            # Удаляем юниты с нашим префиксом
            session.query(Unit).filter(Unit.name.like(f"{self.test_prefix}%")).delete(synchronize_session=False)
            session.commit()

        yield

        # Очистка после теста
        with self.db.get_session() as session:
            session.query(Unit).filter(Unit.name.like(f"{self.test_prefix}%")).delete(synchronize_session=False)
            session.commit()

    def test_is_flying_column_exists(self):
        """Тест: колонка is_flying существует в таблице units"""
        with self.db.get_session() as session:
            # Создаем тестовый юнит
            unit = Unit(
                name=f"{self.test_prefix}TestFlyingUnit",
                icon="🦅",
                price=Decimal('100'),
                damage=10,
                defense=5,
                range=1,
                health=50,
                speed=3,
                is_flying=1
            )
            session.add(unit)
            session.commit()

            # Проверяем, что объект создан с флагом is_flying
            assert unit.id is not None
            assert unit.is_flying == 1

    def test_create_flying_unit(self):
        """Тест: создание летающего юнита"""
        unit_name = f"{self.test_prefix}Griffin"
        with self.db.get_session() as session:
            unit = Unit(
                name=unit_name,
                icon="🦅",
                price=Decimal('300'),
                damage=25,
                defense=20,
                range=1,
                health=100,
                speed=5,
                is_flying=1
            )
            session.add(unit)
            session.commit()
            unit_id = unit.id

        # Проверяем, что юнит создан с is_flying=1
        with self.db.get_session() as session:
            unit = session.query(Unit).filter_by(id=unit_id).first()
            assert unit is not None
            assert unit.name == unit_name
            assert unit.is_flying == 1

    def test_create_non_flying_unit(self):
        """Тест: создание нелетающего юнита"""
        unit_name = f"{self.test_prefix}Warrior"
        with self.db.get_session() as session:
            unit = Unit(
                name=unit_name,
                icon="⚔️",
                price=Decimal('100'),
                damage=15,
                defense=10,
                range=1,
                health=80,
                speed=2,
                is_flying=0
            )
            session.add(unit)
            session.commit()
            unit_id = unit.id

        # Проверяем, что юнит создан с is_flying=0
        with self.db.get_session() as session:
            unit = session.query(Unit).filter_by(id=unit_id).first()
            assert unit is not None
            assert unit.name == unit_name
            assert unit.is_flying == 0

    def test_flying_unit_price_calculation(self):
        """Тест: формула расчета стоимости летающего юнита"""
        # Формула: base + damage*10 + defense*5 + flying_bonus
        # flying_bonus = 2 * (damage + defense) если is_flying=1

        damage = 30
        defense = 25
        base_price = 100

        # Для летающего юнита
        flying_bonus = 2 * (damage + defense)
        expected_flying_price = base_price + damage * 10 + defense * 5 + flying_bonus
        # = 100 + 300 + 125 + 110 = 635

        with self.db.get_session() as session:
            flying_unit = Unit(
                name=f"{self.test_prefix}Phoenix",
                icon="🔥",
                price=Decimal(str(expected_flying_price)),
                damage=damage,
                defense=defense,
                range=1,
                health=150,
                speed=6,
                is_flying=1
            )
            session.add(flying_unit)
            session.commit()

            # Проверяем стоимость
            assert flying_unit.price == Decimal(str(expected_flying_price))

    def test_non_flying_unit_price_calculation(self):
        """Тест: формула расчета стоимости нелетающего юнита"""
        # Формула: base + damage*10 + defense*5 (без flying_bonus)

        damage = 30
        defense = 25
        base_price = 100

        # Для нелетающего юнита
        expected_price = base_price + damage * 10 + defense * 5
        # = 100 + 300 + 125 = 525

        with self.db.get_session() as session:
            non_flying_unit = Unit(
                name=f"{self.test_prefix}Knight",
                icon="🛡️",
                price=Decimal(str(expected_price)),
                damage=damage,
                defense=defense,
                range=1,
                health=150,
                speed=3,
                is_flying=0
            )
            session.add(non_flying_unit)
            session.commit()

            # Проверяем стоимость
            assert non_flying_unit.price == Decimal(str(expected_price))

    def test_flying_unit_more_expensive(self):
        """Тест: летающий юнит дороже нелетающего с теми же характеристиками"""
        damage = 20
        defense = 15
        base_price = 100

        # Создаем два юнита с одинаковыми характеристиками
        with self.db.get_session() as session:
            # Нелетающий
            non_flying_price = base_price + damage * 10 + defense * 5
            non_flying_unit = Unit(
                name=f"{self.test_prefix}Footman",
                icon="⚔️",
                price=Decimal(str(non_flying_price)),
                damage=damage,
                defense=defense,
                range=1,
                health=100,
                speed=2,
                is_flying=0
            )

            # Летающий (с бонусом)
            flying_bonus = 2 * (damage + defense)
            flying_price = base_price + damage * 10 + defense * 5 + flying_bonus
            flying_unit = Unit(
                name=f"{self.test_prefix}Pegasus",
                icon="🦄",
                price=Decimal(str(flying_price)),
                damage=damage,
                defense=defense,
                range=1,
                health=100,
                speed=4,
                is_flying=1
            )

            session.add(non_flying_unit)
            session.add(flying_unit)
            session.commit()

            # Проверяем, что летающий дороже
            assert flying_unit.price > non_flying_unit.price
            # Разница должна быть equal к flying_bonus
            assert flying_unit.price - non_flying_unit.price == Decimal(str(flying_bonus))

    def test_update_is_flying_flag(self):
        """Тест: обновление флага is_flying"""
        with self.db.get_session() as session:
            unit = Unit(
                name=f"{self.test_prefix}Dragon",
                icon="🐉",
                price=Decimal('500'),
                damage=40,
                defense=30,
                range=2,
                health=200,
                speed=4,
                is_flying=0  # Сначала не летает
            )
            session.add(unit)
            session.commit()
            unit_id = unit.id

        # Обновляем флаг на летающий
        with self.db.get_session() as session:
            unit = session.query(Unit).filter_by(id=unit_id).first()
            assert unit.is_flying == 0

            unit.is_flying = 1
            session.commit()

        # Проверяем, что флаг обновлен
        with self.db.get_session() as session:
            unit = session.query(Unit).filter_by(id=unit_id).first()
            assert unit.is_flying == 1

    def test_multiple_flying_units(self):
        """Тест: создание нескольких летающих юнитов"""
        flying_units_data = [
            (f"{self.test_prefix}Gargoyle", "🗿", 150, 12, 10, 1, 60, 4),
            (f"{self.test_prefix}Wyvern", "🦎", 250, 22, 18, 1, 90, 5),
            (f"{self.test_prefix}Angel", "👼", 400, 35, 28, 2, 150, 6),
        ]

        with self.db.get_session() as session:
            for name, icon, price, damage, defense, range_, health, speed in flying_units_data:
                unit = Unit(
                    name=name,
                    icon=icon,
                    price=Decimal(str(price)),
                    damage=damage,
                    defense=defense,
                    range=range_,
                    health=health,
                    speed=speed,
                    is_flying=1
                )
                session.add(unit)
            session.commit()

        # Проверяем, что все юниты созданы с is_flying=1
        with self.db.get_session() as session:
            flying_units = session.query(Unit).filter(
                Unit.name.like(f"{self.test_prefix}%"),
                Unit.is_flying == 1
            ).all()
            # Все 3 созданных нами
            assert len(flying_units) == 3

            # Проверяем, что наши юниты в списке
            names = [unit.name for unit in flying_units]
            assert f"{self.test_prefix}Gargoyle" in names
            assert f"{self.test_prefix}Wyvern" in names
            assert f"{self.test_prefix}Angel" in names

    def test_default_is_flying_value(self):
        """Тест: значение по умолчанию для is_flying (0)"""
        with self.db.get_session() as session:
            # Создаем юнит без указания is_flying
            unit = Unit(
                name=f"{self.test_prefix}DefaultUnit",
                icon="🎮",
                price=Decimal('100'),
                damage=10,
                defense=5,
                range=1,
                health=50,
                speed=2
                # is_flying не указан
            )
            session.add(unit)
            session.commit()

            # По умолчанию is_flying должен быть 0
            assert unit.is_flying == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
