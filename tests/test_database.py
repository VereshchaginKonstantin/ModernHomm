#!/usr/bin/env python3
"""
Интеграционные тесты для модуля database
"""

import pytest
from datetime import datetime
from db import User, Message


class TestDatabase:
    """Тесты для работы с базой данных"""

    def test_create_tables(self, db):
        """Тест создания таблиц"""
        # Таблицы должны быть созданы фикстурой
        with db.get_session() as session:
            # Проверяем, что можем выполнить запрос
            users = session.query(User).all()
            messages = session.query(Message).all()
            assert users == []
            assert messages == []

    def test_save_new_user(self, db):
        """Тест сохранения нового пользователя"""
        user = db.save_user(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )

        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert isinstance(user.first_seen, datetime)
        assert isinstance(user.last_seen, datetime)

    def test_update_existing_user(self, db):
        """Тест обновления существующего пользователя"""
        # Создаем пользователя
        user1 = db.save_user(
            telegram_id=123456789,
            username="oldusername",
            first_name="Old",
            last_name="Name"
        )

        first_seen = user1.first_seen

        # Обновляем того же пользователя с новыми данными
        user2 = db.save_user(
            telegram_id=123456789,
            username="newusername",
            first_name="New",
            last_name="Name"
        )

        assert user2.telegram_id == 123456789
        assert user2.username == "newusername"
        assert user2.first_name == "New"
        assert user2.last_name == "Name"

        # first_seen не должен измениться
        assert user2.first_seen == first_seen

        # Проверяем, что в базе только один пользователь
        users = db.get_all_users()
        assert len(users) == 1

    def test_save_message(self, db):
        """Тест сохранения сообщения"""
        message = db.save_message(
            telegram_user_id=123456789,
            message_text="Hello, world!",
            username="testuser"
        )

        assert message.telegram_user_id == 123456789
        assert message.message_text == "Hello, world!"
        assert message.username == "testuser"
        assert isinstance(message.message_date, datetime)

    def test_save_multiple_messages(self, db):
        """Тест сохранения нескольких сообщений"""
        # Сохраняем несколько сообщений от одного пользователя
        msg1 = db.save_message(123456789, "Message 1", "user1")
        msg2 = db.save_message(123456789, "Message 2", "user1")
        msg3 = db.save_message(987654321, "Message 3", "user2")

        # Получаем сообщения первого пользователя
        user1_messages = db.get_user_messages(123456789)
        assert len(user1_messages) == 2

        # Проверяем, что сообщения отсортированы по дате (самые новые первые)
        assert user1_messages[0].message_text == "Message 2"
        assert user1_messages[1].message_text == "Message 1"

        # Получаем сообщения второго пользователя
        user2_messages = db.get_user_messages(987654321)
        assert len(user2_messages) == 1
        assert user2_messages[0].message_text == "Message 3"

    def test_get_user_messages_empty(self, db):
        """Тест получения сообщений для пользователя без сообщений"""
        messages = db.get_user_messages(999999999)
        assert messages == []

    def test_get_all_users(self, db):
        """Тест получения всех пользователей"""
        # Сохраняем несколько пользователей
        db.save_user(123456789, "user1", "First1", "Last1")
        db.save_user(987654321, "user2", "First2", "Last2")
        db.save_user(111222333, "user3", "First3", "Last3")

        users = db.get_all_users()
        assert len(users) == 3

        telegram_ids = [user.telegram_id for user in users]
        assert 123456789 in telegram_ids
        assert 987654321 in telegram_ids
        assert 111222333 in telegram_ids

    def test_user_without_username(self, db):
        """Тест сохранения пользователя без username"""
        user = db.save_user(
            telegram_id=123456789,
            username=None,
            first_name="Test",
            last_name="User"
        )

        assert user.telegram_id == 123456789
        assert user.username is None
        assert user.first_name == "Test"

    def test_message_without_username(self, db):
        """Тест сохранения сообщения без username"""
        message = db.save_message(
            telegram_user_id=123456789,
            message_text="Test message",
            username=None
        )

        assert message.telegram_user_id == 123456789
        assert message.message_text == "Test message"
        assert message.username is None

    def test_long_message_text(self, db):
        """Тест сохранения длинного сообщения"""
        long_text = "A" * 5000  # Очень длинное сообщение

        message = db.save_message(
            telegram_user_id=123456789,
            message_text=long_text,
            username="testuser"
        )

        assert message.message_text == long_text
        assert len(message.message_text) == 5000

    def test_concurrent_user_saves(self, db):
        """Тест параллельного сохранения одного и того же пользователя"""
        # Симулируем ситуацию, когда пользователь отправляет несколько сообщений подряд
        user1 = db.save_user(123456789, "user1", "First", "Last")
        user2 = db.save_user(123456789, "user1_updated", "First", "Last")
        user3 = db.save_user(123456789, "user1_final", "First", "Last")

        # Должен быть только один пользователь в базе
        users = db.get_all_users()
        assert len(users) == 1
        assert users[0].username == "user1_final"
