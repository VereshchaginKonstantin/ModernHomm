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
from db import Database


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
    async def test_handle_message_unrecognized_command(self, test_config, db, mock_update):
        """Тест ответа на нераспознанную команду"""
        bot = SimpleBot(config_path=test_config, db=db)

        await bot.handle_message(mock_update, None)

        # Проверяем, что ответ был отправлен
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args

        response_text = call_args[0][0]
        # Бот должен ответить что команда не распознана
        assert "Команда не распознана" in response_text or "/help" in response_text

    @pytest.mark.asyncio
    async def test_handle_message_responds_to_any_text(self, test_config, db, mock_update):
        """Тест что бот отвечает на любое текстовое сообщение"""
        bot = SimpleBot(config_path=test_config, db=db)

        mock_update.message.text = "Привет!"
        await bot.handle_message(mock_update, None)

        # Проверяем, что ответ был отправлен
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_with_context(self, test_config, db, mock_update):
        """Тест обработки сообщения с context"""
        bot = SimpleBot(config_path=test_config, db=db)

        # Создаем мок context с user_data
        mock_context = MagicMock()
        mock_context.user_data = {}

        await bot.handle_message(mock_update, mock_context)

        # Проверяем, что ответ был отправлен
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_user_without_username(self, test_config, db, mock_update, mock_user):
        """Тест обработки сообщения от пользователя без username"""
        mock_user.username = None
        mock_update.effective_user = mock_user

        bot = SimpleBot(config_path=test_config, db=db)

        await bot.handle_message(mock_update, None)

        # Проверяем, что ответ был отправлен
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_multiple_messages(self, test_config, db, mock_update):
        """Тест обработки нескольких сообщений"""
        bot = SimpleBot(config_path=test_config, db=db)

        # Отправляем три сообщения
        mock_update.message.text = "Первое сообщение"
        await bot.handle_message(mock_update, None)

        mock_update.message.reply_text.reset_mock()
        mock_update.message.text = "Второе сообщение"
        await bot.handle_message(mock_update, None)

        mock_update.message.reply_text.reset_mock()
        mock_update.message.text = "Третье сообщение"
        await bot.handle_message(mock_update, None)

        # Проверяем, что на каждое сообщение был ответ
        mock_update.message.reply_text.assert_called_once()

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
        mock_update.message.reply_text.reset_mock()
        mock_update.effective_user.id = 222222222
        mock_update.effective_user.username = "user2"
        mock_update.message.text = "Сообщение от пользователя 2"
        await bot.handle_message(mock_update, None)

        # Проверяем, что бот ответил
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_exception_handling(self, test_config, db, mock_update):
        """Тест что бот корректно обрабатывает исключения"""
        bot = SimpleBot(config_path=test_config, db=db)

        # Симулируем исключение при отправке ответа
        mock_update.message.reply_text.side_effect = Exception("Network Error")

        # Не должно быть необработанного исключения
        try:
            await bot.handle_message(mock_update, None)
        except Exception:
            pytest.fail("handle_message не должен пробрасывать исключения")
