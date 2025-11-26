#!/usr/bin/env python3
"""
Интеграционные тесты для проверки справочных данных
"""

import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, Unit, Field


# URL для тестовой базы данных
# Используем Docker контейнер на порту 5433
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/telegram_bot_test"


@pytest.fixture(scope="module")
def db_engine():
    """Создание движка для тестовой базы данных"""
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def db_session(db_engine):
    """Создание сессии для тестов"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


class TestUnitsReferenceData:
    """Тесты для проверки справочника юнитов"""

    def test_units_count(self, db_session):
        """Проверка, что создано правильное количество юнитов"""
        units_count = db_session.query(Unit).count()
        assert units_count == 5, f"Ожидается 5 юнитов, найдено {units_count}"

    def test_swordsman_exists(self, db_session):
        """Проверка создания юнита Мечник"""
        unit = db_session.query(Unit).filter_by(name='Мечник').first()
        assert unit is not None, "Юнит 'Мечник' не найден"
        assert unit.icon == '⚔️'
        assert unit.price == Decimal('100.00')
        assert unit.damage == 10
        assert unit.defense == 5
        assert unit.range == 1
        assert unit.health == 50
        assert unit.speed == 1
        assert unit.luck == Decimal('0.0500')
        assert unit.crit_chance == Decimal('0.1000')

    def test_archer_exists(self, db_session):
        """Проверка создания юнита Лучник"""
        unit = db_session.query(Unit).filter_by(name='Лучник').first()
        assert unit is not None, "Юнит 'Лучник' не найден"
        assert unit.icon == '🏹'
        assert unit.price == Decimal('150.00')
        assert unit.damage == 15
        assert unit.defense == 3
        assert unit.range == 3
        assert unit.health == 40
        assert unit.speed == 1
        assert unit.luck == Decimal('0.1000')
        assert unit.crit_chance == Decimal('0.1500')

    def test_knight_exists(self, db_session):
        """Проверка создания юнита Рыцарь"""
        unit = db_session.query(Unit).filter_by(name='Рыцарь').first()
        assert unit is not None, "Юнит 'Рыцарь' не найден"
        assert unit.icon == '🛡️'
        assert unit.price == Decimal('300.00')
        assert unit.damage == 20
        assert unit.defense == 15
        assert unit.range == 1
        assert unit.health == 100
        assert unit.speed == 1
        assert unit.luck == Decimal('0.0300')
        assert unit.crit_chance == Decimal('0.0800')

    def test_mage_exists(self, db_session):
        """Проверка создания юнита Маг"""
        unit = db_session.query(Unit).filter_by(name='Маг').first()
        assert unit is not None, "Юнит 'Маг' не найден"
        assert unit.icon == '🔮'
        assert unit.price == Decimal('250.00')
        assert unit.damage == 25
        assert unit.defense == 2
        assert unit.range == 4
        assert unit.health == 35
        assert unit.speed == 1
        assert unit.luck == Decimal('0.1500')
        assert unit.crit_chance == Decimal('0.2000')

    def test_dragon_exists(self, db_session):
        """Проверка создания юнита Дракон"""
        unit = db_session.query(Unit).filter_by(name='Дракон').first()
        assert unit is not None, "Юнит 'Дракон' не найден"
        assert unit.icon == '🐉'
        assert unit.price == Decimal('1000.00')
        assert unit.damage == 50
        assert unit.defense == 20
        assert unit.range == 2
        assert unit.health == 200
        assert unit.speed == 2
        assert unit.luck == Decimal('0.2000')
        assert unit.crit_chance == Decimal('0.2500')

    def test_all_units_have_required_fields(self, db_session):
        """Проверка, что у всех юнитов заполнены обязательные поля"""
        units = db_session.query(Unit).all()
        for unit in units:
            assert unit.name is not None and unit.name != ''
            assert unit.icon is not None and unit.icon != ''
            assert unit.price > 0
            assert unit.damage > 0
            assert unit.defense >= 0
            assert unit.range > 0
            assert unit.health > 0
            assert unit.speed > 0
            assert 0 <= unit.luck <= 1
            assert 0 <= unit.crit_chance <= 1


class TestFieldsReferenceData:
    """Тесты для проверки справочника игровых полей"""

    def test_fields_count(self, db_session):
        """Проверка, что создано правильное количество полей"""
        fields_count = db_session.query(Field).count()
        assert fields_count == 3, f"Ожидается 3 поля, найдено {fields_count}"

    def test_field_5x5_exists(self, db_session):
        """Проверка создания поля 5x5"""
        field = db_session.query(Field).filter_by(name='5x5').first()
        assert field is not None, "Поле '5x5' не найдено"
        assert field.width == 5
        assert field.height == 5

    def test_field_7x7_exists(self, db_session):
        """Проверка создания поля 7x7"""
        field = db_session.query(Field).filter_by(name='7x7').first()
        assert field is not None, "Поле '7x7' не найдено"
        assert field.width == 7
        assert field.height == 7

    def test_field_10x10_exists(self, db_session):
        """Проверка создания поля 10x10"""
        field = db_session.query(Field).filter_by(name='10x10').first()
        assert field is not None, "Поле '10x10' не найдено"
        assert field.width == 10
        assert field.height == 10

    def test_all_fields_have_positive_dimensions(self, db_session):
        """Проверка, что у всех полей положительные размеры"""
        fields = db_session.query(Field).all()
        for field in fields:
            assert field.width > 0, f"Поле {field.name} имеет некорректную ширину: {field.width}"
            assert field.height > 0, f"Поле {field.name} имеет некорректную высоту: {field.height}"

    def test_field_names_are_unique(self, db_session):
        """Проверка уникальности имен полей"""
        fields = db_session.query(Field).all()
        field_names = [f.name for f in fields]
        assert len(field_names) == len(set(field_names)), "Найдены дубликаты имен полей"
