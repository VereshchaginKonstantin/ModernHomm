#!/usr/bin/env python3
"""
Интеграционные тесты для бота с базой данных
"""

import pytest
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from bot import SimpleBot
from database import Database


@pytest.fixture
def test_config():
    """Создание тестового конфига"""
    config = {
        "telegram": {
            "bot_token": "test_token_123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "parse_mode": "HTML"
        },
        "bot": {
            "default_response": "Тестовый ответ"
        },
        "database": {
            "url": "postgresql://postgres:postgres@localhost:5433/telegram_bot_test"
        }
    }

    # Создаем временный файл конфига
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        config_path = f.name

    yield config_path

    # Удаляем временный файл после теста
    os.unlink(config_path)


@pytest.fixture
def mock_user():
    """Мок объекта пользователя Telegram"""
    user = MagicMock()
    user.id = 123456789
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    return user


@pytest.fixture
def mock_message(mock_user):
    """Мок объекта сообщения Telegram"""
    message = MagicMock()
    message.text = "Тестовое сообщение"
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def mock_update(mock_user, mock_message):
    """Мок объекта Update от Telegram"""
    update = MagicMock()
    update.effective_user = mock_user
    update.message = mock_message
    return update


class TestBotIntegration:
    """Интеграционные тесты для бота с базой данных"""

    def test_bot_initialization_with_db(self, test_config, db):
        """Тест инициализации бота с базой данных"""
        bot = SimpleBot(config_path=test_config, db=db)

        assert bot.bot_token == "test_token_123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert bot.default_response == "Тестовый ответ"
        assert bot.parse_mode == "HTML"
        assert bot.db is not None

    def test_bot_loads_config(self, test_config, db):
        """Тест загрузки конфигурации"""
        bot = SimpleBot(config_path=test_config, db=db)

        assert bot.config['telegram']['bot_token'] == "test_token_123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert bot.config['bot']['default_response'] == "Тестовый ответ"

    @pytest.mark.asyncio
    async def test_handle_message_saves_user(self, test_config, db, mock_update):
        """Тест сохранения пользователя при получении сообщения"""
        bot = SimpleBot(config_path=test_config, db=db)

        await bot.handle_message(mock_update, None)

        # Проверяем, что пользователь сохранен в базе
        users = db.get_all_users()
        assert len(users) == 1
        assert users[0].telegram_id == 123456789
        assert users[0].username == "testuser"
        assert users[0].first_name == "Test"
        assert users[0].last_name == "User"

    @pytest.mark.asyncio
    async def test_handle_message_saves_message(self, test_config, db, mock_update):
        """Тест сохранения сообщения в базе данных"""
        bot = SimpleBot(config_path=test_config, db=db)

        await bot.handle_message(mock_update, None)

        # Проверяем, что сообщение сохранено
        messages = db.get_user_messages(123456789)
        assert len(messages) == 1
        assert messages[0].telegram_user_id == 123456789
        assert messages[0].message_text == "Тестовое сообщение"
        assert messages[0].username == "testuser"

    @pytest.mark.asyncio
    async def test_handle_message_sends_response_with_username(self, test_config, db, mock_update):
        """Тест отправки ответа с упоминанием username"""
        bot = SimpleBot(config_path=test_config, db=db)

        await bot.handle_message(mock_update, None)

        # Проверяем, что ответ был отправлен с правильным текстом
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args

        response_text = call_args[0][0]
        assert "@testuser" in response_text
        assert "я сохранила твое сообщение" in response_text
        assert "Тестовый ответ" in response_text

    @pytest.mark.asyncio
    async def test_handle_message_user_without_username(self, test_config, db, mock_update, mock_user):
        """Тест обработки сообщения от пользователя без username"""
        mock_user.username = None
        mock_update.effective_user = mock_user

        bot = SimpleBot(config_path=test_config, db=db)

        await bot.handle_message(mock_update, None)

        # Проверяем, что пользователь сохранен без username
        users = db.get_all_users()
        assert len(users) == 1
        assert users[0].username is None

        # Проверяем, что в ответе использовано имя вместо username
        call_args = mock_update.message.reply_text.call_args
        response_text = call_args[0][0]
        assert "Test," in response_text  # Должно быть имя пользователя

    @pytest.mark.asyncio
    async def test_handle_multiple_messages_from_same_user(self, test_config, db, mock_update):
        """Тест обработки нескольких сообщений от одного пользователя"""
        bot = SimpleBot(config_path=test_config, db=db)

        # Отправляем три сообщения
        mock_update.message.text = "Первое сообщение"
        await bot.handle_message(mock_update, None)

        mock_update.message.text = "Второе сообщение"
        await bot.handle_message(mock_update, None)

        mock_update.message.text = "Третье сообщение"
        await bot.handle_message(mock_update, None)

        # Проверяем, что все сообщения сохранены
        messages = db.get_user_messages(123456789)
        assert len(messages) == 3

        # Проверяем, что пользователь один
        users = db.get_all_users()
        assert len(users) == 1

    @pytest.mark.asyncio
    async def test_handle_messages_from_different_users(self, test_config, db, mock_update):
        """Тест обработки сообщений от разных пользователей"""
        bot = SimpleBot(config_path=test_config, db=db)

        # Первый пользователь
        mock_update.effective_user.id = 111111111
        mock_update.effective_user.username = "user1"
        mock_update.message.text = "Сообщение от пользователя 1"
        await bot.handle_message(mock_update, None)

        # Второй пользователь
        mock_update.effective_user.id = 222222222
        mock_update.effective_user.username = "user2"
        mock_update.message.text = "Сообщение от пользователя 2"
        await bot.handle_message(mock_update, None)

        # Третий пользователь
        mock_update.effective_user.id = 333333333
        mock_update.effective_user.username = "user3"
        mock_update.message.text = "Сообщение от пользователя 3"
        await bot.handle_message(mock_update, None)

        # Проверяем, что все пользователи сохранены
        users = db.get_all_users()
        assert len(users) == 3

        # Проверяем сообщения каждого пользователя
        messages1 = db.get_user_messages(111111111)
        messages2 = db.get_user_messages(222222222)
        messages3 = db.get_user_messages(333333333)

        assert len(messages1) == 1
        assert len(messages2) == 1
        assert len(messages3) == 1

    @pytest.mark.asyncio
    async def test_handle_message_db_error_still_responds(self, test_config, db, mock_update):
        """Тест что бот отвечает даже при ошибке в БД"""
        bot = SimpleBot(config_path=test_config, db=db)

        # Симулируем ошибку БД
        with patch.object(db, 'save_user', side_effect=Exception("DB Error")):
            await bot.handle_message(mock_update, None)

            # Проверяем, что ответ всё равно был отправлен
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]

            # Должен быть отправлен стандартный ответ
            assert "Тестовый ответ" in response_text
