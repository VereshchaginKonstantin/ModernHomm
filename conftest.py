#!/usr/bin/env python3
"""
Конфигурация pytest и фикстуры для тестов
"""

import pytest
import os
from db import Database


@pytest.fixture(scope="session")
def test_db_url():
    """Строка подключения к тестовой базе данных"""
    return os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5433/telegram_bot_test'
    )


@pytest.fixture(scope="function")
def db(test_db_url):
    """
    Фикстура для создания чистой базы данных для каждого теста

    Yields:
        Database: Объект базы данных
    """
    database = Database(test_db_url)

    # Удаляем и создаем таблицы заново для каждого теста
    database.drop_tables()
    database.create_tables()

    yield database

    # Очистка после теста
    database.drop_tables()


@pytest.fixture(scope="function")
def db_session(db):
    """
    Фикстура для создания сессии базы данных для теста

    Yields:
        Session: Объект сессии SQLAlchemy
    """
    with db.get_session() as session:
        yield session
