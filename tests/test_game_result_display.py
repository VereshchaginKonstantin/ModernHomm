#!/usr/bin/env python3
"""
Интеграционные тесты для вывода результатов игры после завершения
"""

import pytest
import json
import tempfile
import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call
from telegram import Update, CallbackQuery, InlineKeyboardMarkup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot import SimpleBot
from db import Database
from db.models import Base, GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field
from game_engine import GameEngine


@pytest.fixture(scope="function")
def db_session():
    """Создание тестовой сессии базы данных"""
    from sqlalchemy import text
    engine = create_engine("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Очищаем тестовые данные перед тестом
    try:
        session.execute(text("DELETE FROM battle_units"))
        session.execute(text("DELETE FROM game_logs"))
        session.execute(text("DELETE FROM games"))
        session.execute(text("DELETE FROM user_units"))
        session.execute(text("DELETE FROM game_users"))
        session.commit()
    except Exception:
        session.rollback()

    yield session

    # Очищаем тестовые данные после теста
    try:
        session.execute(text("DELETE FROM battle_units"))
        session.execute(text("DELETE FROM game_logs"))
        session.execute(text("DELETE FROM games"))
        session.execute(text("DELETE FROM user_units"))
        session.execute(text("DELETE FROM game_users"))
        session.commit()
    except Exception:
        session.rollback()

    session.close()


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
        },
        "game": {
            "initial_balance": 1000
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
def setup_test_database(db_session):
    """Настройка тестовой базы данных с игроками и юнитами"""
    # Создать юниты
    infantry = Unit(
        name="Пехота",
        icon="⚔️",
        damage=30,
        defense=5,
        health=50,
        speed=2,
        range=5,  # Большая дальность для тестов
        price=Decimal('100.00'),
        crit_chance=0.1,
        luck=0.1,
        image_path="/tmp/test_infantry.png"
    )

    sniper = Unit(
        name="Снайпер",
        icon="🎯",
        damage=20,
        defense=2,
        health=30,
        speed=2,
        range=5,
        price=Decimal('150.00'),
        crit_chance=0.3,
        luck=0.15,
        image_path="/tmp/test_sniper.png"
    )

    db_session.add(infantry)
    db_session.add(sniper)
    db_session.commit()

    # Создать изображения для юнитов (заглушки)
    for path in ["/tmp/test_infantry.png", "/tmp/test_sniper.png"]:
        if not os.path.exists(path):
            with open(path, 'wb') as f:
                # Создаем минимальный PNG файл (1x1 пиксель)
                f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')

    # Создать двух игроков
    player1 = GameUser(
        telegram_id=111,
        name="Player1",
        balance=Decimal('1000.00'),
        wins=0,
        losses=0
    )
    player2 = GameUser(
        telegram_id=222,
        name="Player2",
        balance=Decimal('1000.00'),
        wins=0,
        losses=0
    )

    db_session.add(player1)
    db_session.add(player2)
    db_session.commit()

    # Дать игрокам юнитов
    player1_units = UserUnit(
        game_user_id=player1.id,
        unit_type_id=infantry.id,
        count=10
    )
    player2_units = UserUnit(
        game_user_id=player2.id,
        unit_type_id=sniper.id,
        count=1
    )

    db_session.add(player1_units)
    db_session.add(player2_units)
    db_session.commit()

    return {
        "player1": player1,
        "player2": player2,
        "infantry": infantry,
        "sniper": sniper
    }


@pytest.mark.asyncio
async def test_game_completion_sends_results_to_both_players(test_config, db_session, setup_test_database):
    """
    Тест: После завершения игры результаты отправляются обоим игрокам
    и кнопки удаляются из интерфейса
    """
    data = setup_test_database
    player1 = data["player1"]
    player2 = data["player2"]

    # Создать Database с тестовой сессией
    test_db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

    # Создать бота
    bot = SimpleBot(config_path=test_config, db=test_db)

    # Создать игру через GameEngine
    with test_db.get_session() as session:
        engine = GameEngine(session)
        game, msg = engine.create_game(player1.id, player2.name, "5x5")
        assert game is not None
        game_id = game.id

        # Принять игру
        success, msg = engine.accept_game(game_id, player2.id)
        assert success

    # Мокируем объекты Telegram
    mock_query = MagicMock(spec=CallbackQuery)
    mock_query.answer = AsyncMock()
    mock_query.from_user = MagicMock()
    mock_query.from_user.id = player1.telegram_id
    mock_query.data = f"game_attack:{game_id}:1:2"  # будет заменено реальными ID

    # Получить реальные ID юнитов
    with test_db.get_session() as session:
        attacker = session.query(BattleUnit).filter(
            BattleUnit.game_id == game_id,
            BattleUnit.player_id == player1.id
        ).first()
        target = session.query(BattleUnit).filter(
            BattleUnit.game_id == game_id,
            BattleUnit.player_id == player2.id
        ).first()

        assert attacker is not None
        assert target is not None
        mock_query.data = f"game_attack:{game_id}:{attacker.id}:{target.id}"

    mock_query.message = MagicMock()
    mock_query.message.photo = []  # Нет фото

    mock_update = MagicMock(spec=Update)
    mock_update.callback_query = mock_query
    mock_update.effective_user = MagicMock()
    mock_update.effective_user.id = player1.telegram_id

    mock_context = MagicMock()
    mock_context.bot = MagicMock()
    mock_context.bot.send_message = AsyncMock()

    # Мокируем методы редактирования
    with patch.object(bot, '_edit_field', new=AsyncMock()) as mock_edit_field:
        # Выполнить несколько атак до завершения игры
        max_attempts = 20
        for attempt in range(max_attempts):
            await bot.game_attack_callback(mock_update, mock_context)

            # Проверить статус игры
            game = test_db.get_game_by_id(game_id)
            if game.status == GameStatus.COMPLETED:
                break

            # Обновить данные для следующей атаки
            with test_db.get_session() as session:
                attacker = session.query(BattleUnit).filter(
                    BattleUnit.game_id == game_id,
                    BattleUnit.player_id == player1.id,
                    BattleUnit.has_moved == 0
                ).first()
                target = session.query(BattleUnit).filter(
                    BattleUnit.game_id == game_id,
                    BattleUnit.player_id == player2.id
                ).first()

                if not attacker or not target:
                    break

                mock_query.data = f"game_attack:{game_id}:{attacker.id}:{target.id}"

        # Проверить что игра завершена
        game = test_db.get_game_by_id(game_id)
        assert game.status == GameStatus.COMPLETED, "Игра должна быть завершена"
        assert game.winner_id == player1.id, "Победителем должен быть Player1"

        # Проверить что _edit_field был вызван с пустой клавиатурой (кнопки удалены)
        last_call_args = mock_edit_field.call_args
        assert last_call_args is not None, "_edit_field должен быть вызван"

        # Проверить что клавиатура пустая (кнопки удалены)
        # call_args возвращает (args, kwargs), где args - позиционные аргументы, kwargs - именованные
        if 'keyboard' in last_call_args[1]:
            keyboard_arg = last_call_args[1]['keyboard']
        else:
            # Если keyboard передан позиционно, это 4-й аргумент (индекс 3)
            keyboard_arg = last_call_args[0][3] if len(last_call_args[0]) > 3 else []
        assert keyboard_arg == [], "Клавиатура должна быть пустой после завершения игры"

        # Проверить что в сообщении есть информация о результатах
        caption_arg = last_call_args[0][2]
        assert "ИГРА ЗАВЕРШЕНА" in caption_arg, "Должно быть сообщение о завершении игры"
        assert "Победитель" in caption_arg, "Должна быть информация о победителе"
        assert "Player1" in caption_arg, "Должно быть имя победителя"

        # Проверить что результаты отправлены противнику
        assert mock_context.bot.send_message.called, "Результаты должны быть отправлены противнику"
        sent_messages = [call_item[1]['text'] for call_item in mock_context.bot.send_message.call_args_list]
        assert any("ИГРА ЗАВЕРШЕНА" in msg for msg in sent_messages), "Противник должен получить результаты"


@pytest.mark.asyncio
async def test_game_completion_updates_statistics(test_config, db_session, setup_test_database):
    """
    Тест: После завершения игры статистика игроков обновляется корректно
    """
    data = setup_test_database
    player1 = data["player1"]
    player2 = data["player2"]

    test_db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

    # Создать игру
    with test_db.get_session() as session:
        engine = GameEngine(session)
        game, msg = engine.create_game(player1.id, player2.name, "5x5")
        game_id = game.id
        engine.accept_game(game_id, player2.id)

        # Симулировать атаки до завершения
        max_turns = 50
        for turn in range(max_turns):
            attacker = session.query(BattleUnit).filter(
                BattleUnit.game_id == game_id,
                BattleUnit.has_moved == 0
            ).first()
            target = session.query(BattleUnit).filter(
                BattleUnit.game_id == game_id,
                BattleUnit.player_id != attacker.player_id if attacker else None
            ).first()

            if not attacker or not target:
                break

            success, msg, _ = engine.attack(game_id, attacker.player_id, attacker.id, target.id)
            if not success:
                break

            session.refresh(game)
            if game.status == GameStatus.COMPLETED:
                break

    # Проверить статистику - нужно получить игроков заново из БД
    with test_db.get_session() as check_session:
        updated_player1 = check_session.query(GameUser).filter_by(id=player1.id).first()
        updated_player2 = check_session.query(GameUser).filter_by(id=player2.id).first()

        assert updated_player1.wins == 1, "У победителя должна быть 1 победа"
        assert updated_player1.losses == 0, "У победителя не должно быть поражений"
        assert updated_player2.wins == 0, "У проигравшего не должно быть побед"
        assert updated_player2.losses == 1, "У проигравшего должно быть 1 поражение"


@pytest.mark.asyncio
async def test_game_completion_clears_game_field_buttons(test_config, db_session, setup_test_database):
    """
    Тест: После завершения игры кнопки управления игрой удаляются
    """
    data = setup_test_database
    player1 = data["player1"]
    player2 = data["player2"]

    test_db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")
    bot = SimpleBot(config_path=test_config, db=test_db)

    # Создать и завершить игру
    with test_db.get_session() as session:
        engine = GameEngine(session)
        game, msg = engine.create_game(player1.id, player2.name, "5x5")
        game_id = game.id
        engine.accept_game(game_id, player2.id)

    # Получить доступные действия до завершения игры
    with test_db.get_session() as session:
        engine = GameEngine(session)
        actions_before = engine.get_available_actions(game_id, player1.id)

    # Действия должны быть доступны
    assert actions_before.get("action") == "play", "До завершения игры должны быть доступны действия"

    # Завершить игру принудительно
    game = test_db.get_game_by_id(game_id)
    game.status = GameStatus.COMPLETED
    game.winner_id = player1.id
    with test_db.get_session() as session:
        session.merge(game)
        session.commit()

    # Получить доступные действия после завершения
    with test_db.get_session() as session:
        engine = GameEngine(session)
        actions_after = engine.get_available_actions(game_id, player1.id)

    # Действия не должны быть доступны
    assert actions_after.get("action") == "none", "После завершения игры не должно быть доступных действий"

    # Проверить что клавиатура пустая
    keyboard = bot._create_game_keyboard(game_id, player1.id, actions_after)
    assert keyboard == [], "Клавиатура должна быть пустой после завершения игры"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
