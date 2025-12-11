#!/usr/bin/env python3
"""
Интеграционные тесты для команды /startRegistrationAmount
"""

import pytest
from db import Database
from db.models import Config, GameUser


@pytest.fixture
def test_db():
    """Фикстура для тестовой базы данных"""
    db = Database('postgresql://postgres:postgres@localhost:5433/telegram_bot_test')
    db.create_tables()
    yield db
    db.drop_tables()


def test_config_table_exists(test_db):
    """Проверка, что таблица config существует"""
    with test_db.get_session() as session:
        # Попытка запросить config должна работать
        configs = session.query(Config).all()
        assert isinstance(configs, list)


def test_get_config_default_value(test_db):
    """Проверка получения значения по умолчанию"""
    # Если ключа нет, должен вернуться default
    value = test_db.get_config('nonexistent_key', '500')
    assert value == '500'


def test_set_and_get_config(test_db):
    """Проверка установки и получения значения конфигурации"""
    # Устанавливаем значение
    config = test_db.set_config(
        key='start_registration_amount',
        value='2000',
        description='Test value'
    )

    assert config.key == 'start_registration_amount'
    assert config.value == '2000'
    assert config.description == 'Test value'

    # Получаем значение
    value = test_db.get_config('start_registration_amount')
    assert value == '2000'


def test_update_existing_config(test_db):
    """Проверка обновления существующего значения конфигурации"""
    # Создаем начальное значение
    test_db.set_config(
        key='start_registration_amount',
        value='1000',
        description='Initial value'
    )

    # Обновляем значение
    test_db.set_config(
        key='start_registration_amount',
        value='3000',
        description='Updated value'
    )

    # Проверяем, что значение обновилось
    value = test_db.get_config('start_registration_amount')
    assert value == '3000'

    # Проверяем, что в базе только одна запись
    with test_db.get_session() as session:
        count = session.query(Config).filter_by(key='start_registration_amount').count()
        assert count == 1


def test_game_user_creation_with_custom_initial_balance(test_db):
    """Проверка создания игрового пользователя с кастомной стартовой суммой"""
    # Устанавливаем кастомную стартовую сумму
    test_db.set_config(
        key='start_registration_amount',
        value='5000'
    )

    # Создаем игрового пользователя
    game_user = test_db.create_game_user(
        telegram_id=123456,
        name='TestPlayer',
        initial_balance=float(test_db.get_config('start_registration_amount', '1000'))
    )

    assert game_user.balance == 5000


def test_config_persistence(test_db):
    """Проверка, что конфигурация сохраняется между сессиями"""
    # Устанавливаем значение в первой сессии
    test_db.set_config(
        key='start_registration_amount',
        value='7500'
    )

    # Создаем новый экземпляр Database (имитируя перезапуск)
    new_db = Database('postgresql://postgres:postgres@localhost:5433/telegram_bot_test')

    # Получаем значение через новый экземпляр
    value = new_db.get_config('start_registration_amount')
    assert value == '7500'


def test_multiple_configs(test_db):
    """Проверка работы с несколькими значениями конфигурации"""
    # Устанавливаем несколько значений
    test_db.set_config('key1', 'value1', 'Description 1')
    test_db.set_config('key2', 'value2', 'Description 2')
    test_db.set_config('key3', 'value3', 'Description 3')

    # Проверяем, что все значения доступны
    assert test_db.get_config('key1') == 'value1'
    assert test_db.get_config('key2') == 'value2'
    assert test_db.get_config('key3') == 'value3'

    # Проверяем, что в базе 3 записи
    with test_db.get_session() as session:
        count = session.query(Config).count()
        assert count == 3


def test_config_with_numeric_value(test_db):
    """Проверка работы с числовыми значениями конфигурации"""
    # Устанавливаем числовое значение как строку
    test_db.set_config('start_registration_amount', '12345.67')

    # Получаем и конвертируем в float
    value = test_db.get_config('start_registration_amount')
    numeric_value = float(value)

    assert numeric_value == 12345.67


def test_config_unique_key_constraint(test_db):
    """Проверка, что ключи конфигурации уникальны"""
    # Создаем значение
    test_db.set_config('unique_key', 'value1')

    # Обновляем то же значение (должно обновиться, а не создаться дубликат)
    test_db.set_config('unique_key', 'value2')

    # Проверяем, что в базе только одна запись с этим ключом
    with test_db.get_session() as session:
        count = session.query(Config).filter_by(key='unique_key').count()
        assert count == 1

        config = session.query(Config).filter_by(key='unique_key').first()
        assert config.value == 'value2'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
