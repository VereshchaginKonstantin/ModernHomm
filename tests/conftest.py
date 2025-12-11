#!/usr/bin/env python3
"""
Pytest fixtures for test suite.
Merged conftest with fixtures for all test types.
"""

import os
import pytest
from db import Database, Base, User, Message, GameUser, UserUnit, Game
from sqlalchemy import create_engine, text


@pytest.fixture(scope="session")
def test_db_url():
    """Connection string for the test database"""
    return os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5433/telegram_bot_test'
    )


@pytest.fixture(scope="function")
def db(test_db_url):
    """
    Database fixture for tests.
    Creates a fresh database connection for each test.
    Only cleans transactional data (users, messages), not reference data.
    """
    database = Database(test_db_url)
    engine = create_engine(test_db_url)

    # Clean transactional data before test (but keep reference data from migrations)
    # Only clean if tables exist (they should from migrations)
    try:
        with database.get_session() as session:
            # Clean game-related data (in correct order due to foreign keys)
            session.execute(text("DELETE FROM battle_units"))
            session.execute(text("DELETE FROM game_logs"))
            session.execute(text("DELETE FROM obstacles"))
            session.execute(text("DELETE FROM games"))
            session.execute(text("DELETE FROM user_units"))
            session.execute(text("DELETE FROM game_users"))
            # Clean user data from old simple bot
            session.execute(text("DELETE FROM messages"))
            session.execute(text("DELETE FROM users"))
            # Clean image-related data
            session.execute(text("DELETE FROM unit_images"))
            session.execute(text("DELETE FROM settings"))
            session.commit()
    except Exception as e:
        # Tables might not exist yet, that's OK
        try:
            session.rollback()
        except:
            pass

    yield database

    # Clean up after test
    try:
        with database.get_session() as session:
            session.execute(text("DELETE FROM battle_units"))
            session.execute(text("DELETE FROM game_logs"))
            session.execute(text("DELETE FROM obstacles"))
            session.execute(text("DELETE FROM games"))
            session.execute(text("DELETE FROM user_units"))
            session.execute(text("DELETE FROM game_users"))
            # Clean image-related data
            session.execute(text("DELETE FROM unit_images"))
            session.execute(text("DELETE FROM settings"))
            session.execute(text("DELETE FROM messages"))
            session.execute(text("DELETE FROM users"))
            session.commit()
    except Exception as e:
        # Tables might not exist, that's OK
        try:
            session.rollback()
        except:
            pass

    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db):
    """
    Database session fixture for tests.

    Yields:
        Session: SQLAlchemy session object
    """
    with db.get_session() as session:
        yield session
