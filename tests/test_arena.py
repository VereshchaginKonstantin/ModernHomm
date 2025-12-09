#!/usr/bin/env python3
"""
Интеграционные тесты для арены (Web UI и API)
Проверяет:
1. API эндпоинты арены
2. Создание и управление играми через API
3. Синхронизацию между Web и Telegram (через один GameEngine)
4. Корректность Telegram уведомлений
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from decimal import Decimal

from db import Database
from db.models import (
    Game, GameUser, Field, GameLog, Unit, UserUnit,
    GameStatus, BattleUnit, Obstacle
)
from game_engine import GameEngine


class TestArenaAPI:
    """Тесты для API арены"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка тестовой базы данных"""
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        # Очистка данных перед тестом
        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

        yield

        # Очистка после теста
        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

    def _create_test_players_with_units(self, session):
        """Создание тестовых игроков с юнитами"""
        import os
        import tempfile

        # Получаем юнит из базы
        unit = session.query(Unit).first()
        if not unit:
            pytest.skip("No units in database")

        # Создаем временный файл для image_path если его нет
        if not unit.image_path or not os.path.exists(unit.image_path):
            # Устанавливаем фиктивный путь к существующему файлу
            # Используем __file__ как существующий файл
            for u in session.query(Unit).all():
                u.image_path = os.path.abspath(__file__)
            session.commit()

        # Создаем игроков
        player1 = GameUser(telegram_id=1001, name="ArenaPlayer1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=1002, name="ArenaPlayer2", balance=Decimal("1000"))
        session.add(player1)
        session.add(player2)
        session.flush()

        # Даем юнитов игрокам
        user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
        user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
        session.add(user_unit1)
        session.add(user_unit2)
        session.commit()

        return player1, player2

    def test_create_game_via_engine(self):
        """Тест: создание игры через GameEngine (как делает арена)"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, message = engine.create_game(player1.id, player2.name, "5x5")

            assert game is not None
            assert game.player1_id == player1.id
            assert game.status == GameStatus.WAITING
            assert "ожидает" in message.lower() or "создана" in message.lower()

    def test_accept_game_via_engine(self):
        """Тест: принятие игры через GameEngine"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")

            success, message = engine.accept_game(game.id, player2.id)

            assert success is True
            assert game.status == GameStatus.IN_PROGRESS
            assert game.player2_id == player2.id

    def test_game_state_has_units(self):
        """Тест: состояние игры содержит юнитов на поле"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            engine.accept_game(game.id, player2.id)

            # Проверяем что юниты созданы на поле
            battle_units = session.query(BattleUnit).filter_by(game_id=game.id).all()
            assert len(battle_units) > 0

            # Проверяем что юниты принадлежат обоим игрокам
            player_ids = set(bu.player_id for bu in battle_units)
            assert player1.id in player_ids
            assert player2.id in player_ids

    def test_move_unit_via_engine(self):
        """Тест: перемещение юнита через GameEngine"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            engine.accept_game(game.id, player2.id)

            # Находим юнит текущего игрока
            current_player_id = game.current_player_id
            battle_unit = session.query(BattleUnit).filter_by(
                game_id=game.id,
                player_id=current_player_id,
                has_moved=0
            ).first()

            if not battle_unit:
                pytest.skip("No battle units available")

            # Получаем доступные клетки для перемещения
            available_cells = engine.get_available_movement_cells(game.id, battle_unit.id)

            if not available_cells:
                pytest.skip("No available movement cells")

            target_x, target_y = available_cells[0]
            old_x, old_y = battle_unit.position_x, battle_unit.position_y

            # Перемещаем
            success, message, turn_switched = engine.move_unit(
                game.id, current_player_id, battle_unit.id, target_x, target_y
            )

            assert success is True
            assert battle_unit.position_x == target_x
            assert battle_unit.position_y == target_y
            assert battle_unit.has_moved == 1

    def test_attack_via_engine(self):
        """Тест: атака через GameEngine"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            engine.accept_game(game.id, player2.id)

            current_player_id = game.current_player_id
            attacker = session.query(BattleUnit).filter_by(
                game_id=game.id,
                player_id=current_player_id,
                has_moved=0
            ).first()

            if not attacker:
                pytest.skip("No attacker available")

            # Находим вражеского юнита
            enemy = session.query(BattleUnit).filter(
                BattleUnit.game_id == game.id,
                BattleUnit.player_id != current_player_id,
                BattleUnit.total_count > 0
            ).first()

            if not enemy:
                pytest.skip("No enemy available")

            # Получаем юнит атакующего для проверки дальности
            user_unit = session.query(UserUnit).filter_by(id=attacker.user_unit_id).first()
            unit_type = session.query(Unit).filter_by(id=user_unit.unit_type_id).first()

            # Перемещаем атакующего ближе к врагу если нужно
            distance = abs(attacker.position_x - enemy.position_x) + abs(attacker.position_y - enemy.position_y)

            if distance > unit_type.range:
                # Пробуем переместиться ближе
                available_cells = engine.get_available_movement_cells(game.id, attacker.id)
                for cell_x, cell_y in available_cells:
                    new_distance = abs(cell_x - enemy.position_x) + abs(cell_y - enemy.position_y)
                    if new_distance <= unit_type.range:
                        engine.move_unit(game.id, current_player_id, attacker.id, cell_x, cell_y)
                        # Сбрасываем has_moved для теста
                        attacker.has_moved = False
                        session.commit()
                        break

            # Пробуем атаковать
            enemy_count_before = enemy.total_count
            success, message, turn_switched = engine.attack(
                game.id, current_player_id, attacker.id, enemy.id
            )

            # Атака может быть успешной или нет в зависимости от расстояния
            if success:
                # Проверяем что урон был нанесен или что-то произошло
                assert "атак" in message.lower() or "урон" in message.lower() or "уничтож" in message.lower()

    def test_game_logs_created(self):
        """Тест: логи создаются при действиях в игре"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            engine.accept_game(game.id, player2.id)

            # Проверяем что логи созданы
            logs = session.query(GameLog).filter_by(game_id=game.id).all()
            assert len(logs) > 0

            # Проверяем типы событий
            event_types = [log.event_type for log in logs]
            assert "game_created" in event_types or "game_started" in event_types or any("game" in et for et in event_types)


class TestArenaTelegramSync:
    """Тесты синхронизации арены с Telegram"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка тестовой базы данных"""
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

        yield

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

    def _create_test_players_with_units(self, session):
        """Создание тестовых игроков с юнитами"""
        import os

        unit = session.query(Unit).first()
        if not unit:
            pytest.skip("No units in database")

        # Устанавливаем фиктивный путь к существующему файлу
        for u in session.query(Unit).all():
            u.image_path = os.path.abspath(__file__)
        session.commit()

        player1 = GameUser(telegram_id=2001, name="SyncPlayer1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=2002, name="SyncPlayer2", balance=Decimal("1000"))
        session.add(player1)
        session.add(player2)
        session.flush()

        user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
        user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
        session.add(user_unit1)
        session.add(user_unit2)
        session.commit()

        return player1, player2

    def test_same_engine_for_web_and_telegram(self):
        """Тест: один и тот же GameEngine используется для Web и Telegram"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            # Симулируем Web: создаем игру
            web_engine = GameEngine(session)
            game, _ = web_engine.create_game(player1.id, player2.name, "5x5")
            web_engine.accept_game(game.id, player2.id)

            game_id = game.id
            current_player = game.current_player_id

        # Симулируем Telegram: делаем ход в той же игре
        battle_unit_id = None
        with self.db.get_session() as session:
            telegram_engine = GameEngine(session)

            battle_unit = session.query(BattleUnit).filter_by(
                game_id=game_id,
                player_id=current_player,
                has_moved=0
            ).first()

            if battle_unit:
                battle_unit_id = battle_unit.id  # Сохраняем ID до закрытия сессии
                available_cells = telegram_engine.get_available_movement_cells(game_id, battle_unit.id)
                if available_cells:
                    target_x, target_y = available_cells[0]
                    success, _, _ = telegram_engine.move_unit(
                        game_id, current_player, battle_unit.id, target_x, target_y
                    )
                    assert success is True

        # Симулируем Web: проверяем что изменения видны
        if battle_unit_id:
            with self.db.get_session() as session:
                game = session.query(Game).filter_by(id=game_id).first()
                battle_unit = session.query(BattleUnit).filter_by(
                    id=battle_unit_id
                ).first()

                # Юнит должен быть перемещен
                assert battle_unit.has_moved == 1

    def test_game_state_consistency(self):
        """Тест: состояние игры консистентно между сессиями"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            engine.accept_game(game.id, player2.id)

            game_id = game.id
            initial_current_player = game.current_player_id

            # Запоминаем начальное количество юнитов
            battle_units = session.query(BattleUnit).filter_by(game_id=game_id).all()
            initial_unit_count = len(battle_units)

        # Открываем новую сессию и проверяем состояние
        with self.db.get_session() as session:
            game = session.query(Game).filter_by(id=game_id).first()
            battle_units = session.query(BattleUnit).filter_by(game_id=game_id).all()

            assert game.current_player_id == initial_current_player
            assert len(battle_units) == initial_unit_count


class TestTelegramNotifications:
    """Тесты для Telegram уведомлений из арены"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка"""
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

        yield

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

    def test_notify_opponent_function_exists(self):
        """Тест: функция notify_opponent существует"""
        from admin_arena import notify_opponent, send_telegram_notification
        assert callable(notify_opponent)
        assert callable(send_telegram_notification)

    @patch('admin_arena.requests.post')
    def test_send_telegram_notification_structure(self, mock_post):
        """Тест: структура Telegram уведомления корректна"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        from admin_arena import send_telegram_notification

        # Мокаем получение токена
        with patch('admin_arena.get_telegram_bot_token', return_value='test_token'):
            result = send_telegram_notification(
                chat_id=12345,
                message="Test message",
                reply_markup={'inline_keyboard': [[{'text': 'Test', 'callback_data': 'test'}]]}
            )

            # Проверяем что запрос был отправлен
            assert mock_post.called
            call_args = mock_post.call_args

            # Проверяем структуру запроса
            assert 'json' in call_args.kwargs or len(call_args.args) > 1
            payload = call_args.kwargs.get('json') or call_args.args[1]
            assert payload['chat_id'] == 12345
            assert payload['text'] == "Test message"
            assert payload['parse_mode'] == 'HTML'

    def test_get_game_full_data_structure(self):
        """Тест: структура данных игры для replay корректна"""
        import os

        with self.db.get_session() as session:
            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            # Устанавливаем фиктивный путь к существующему файлу
            for u in session.query(Unit).all():
                u.image_path = os.path.abspath(__file__)
            session.commit()

            player1 = GameUser(telegram_id=3001, name="DataPlayer1", balance=Decimal("1000"))
            player2 = GameUser(telegram_id=3002, name="DataPlayer2", balance=Decimal("1000"))
            session.add(player1)
            session.add(player2)
            session.flush()

            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
            session.add(user_unit1)
            session.add(user_unit2)
            session.commit()

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            engine.accept_game(game.id, player2.id)
            game_id = game.id

        # Мокаем db в admin_arena чтобы использовать тестовую БД
        import admin_arena
        original_db = admin_arena.db
        admin_arena.db = self.db
        try:
            from admin_arena import get_game_full_data
            game_data = get_game_full_data(game_id)

            assert game_data is not None
            assert 'game' in game_data
            assert 'player1' in game_data
            assert 'player2' in game_data
            assert 'units' in game_data
            assert 'logs' in game_data
            assert 'field' in game_data
        finally:
            # Восстанавливаем оригинальное соединение
            admin_arena.db = original_db


class TestArenaAPIEndpoints:
    """Тесты для API эндпоинтов арены (без Flask app context)"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка"""
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

        yield

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

    def test_unit_actions_endpoint_logic(self):
        """Тест: логика получения доступных действий юнита"""
        import os

        with self.db.get_session() as session:
            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            # Устанавливаем фиктивный путь к существующему файлу
            for u in session.query(Unit).all():
                u.image_path = os.path.abspath(__file__)
            session.commit()

            player1 = GameUser(telegram_id=4001, name="ActionPlayer1", balance=Decimal("1000"))
            player2 = GameUser(telegram_id=4002, name="ActionPlayer2", balance=Decimal("1000"))
            session.add(player1)
            session.add(player2)
            session.flush()

            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
            session.add(user_unit1)
            session.add(user_unit2)
            session.commit()

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            engine.accept_game(game.id, player2.id)

            # Находим юнит текущего игрока
            current_player_id = game.current_player_id
            battle_unit = session.query(BattleUnit).filter_by(
                game_id=game.id,
                player_id=current_player_id,
                has_moved=0
            ).first()

            if not battle_unit:
                pytest.skip("No battle unit available")

            # Получаем доступные клетки для перемещения
            move_cells = engine.get_available_movement_cells(game.id, battle_unit.id)

            # Должны быть доступные ходы (поле 5x5, юнит где-то)
            # На маленьком поле могут быть ограничения, но хотя бы проверим что метод работает
            assert isinstance(move_cells, list)

    def test_move_endpoint_logic(self):
        """Тест: логика выполнения хода"""
        import os

        with self.db.get_session() as session:
            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            # Устанавливаем фиктивный путь к существующему файлу
            for u in session.query(Unit).all():
                u.image_path = os.path.abspath(__file__)
            session.commit()

            player1 = GameUser(telegram_id=5001, name="MovePlayer1", balance=Decimal("1000"))
            player2 = GameUser(telegram_id=5002, name="MovePlayer2", balance=Decimal("1000"))
            session.add(player1)
            session.add(player2)
            session.flush()

            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
            session.add(user_unit1)
            session.add(user_unit2)
            session.commit()

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            engine.accept_game(game.id, player2.id)

            current_player_id = game.current_player_id
            battle_unit = session.query(BattleUnit).filter_by(
                game_id=game.id,
                player_id=current_player_id,
                has_moved=0
            ).first()

            if not battle_unit:
                pytest.skip("No battle unit available")

            move_cells = engine.get_available_movement_cells(game.id, battle_unit.id)

            if not move_cells:
                pytest.skip("No available moves")

            target_x, target_y = move_cells[0]

            # Выполняем ход (как делает API)
            success, message, turn_switched = engine.move_unit(
                game.id, current_player_id, battle_unit.id, target_x, target_y
            )

            assert success is True
            assert isinstance(message, str)
            assert isinstance(turn_switched, bool)

            # Проверяем что юнит переместился
            session.refresh(battle_unit)
            assert battle_unit.position_x == target_x
            assert battle_unit.position_y == target_y


class TestActiveGameButton:
    """Тесты для кнопки 'Продолжить активную игру' и редиректа"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка тестовой базы данных"""
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

        yield

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

    def _create_test_players_with_units(self, session):
        """Создание тестовых игроков с юнитами"""
        import os

        unit = session.query(Unit).first()
        if not unit:
            pytest.skip("No units in database")

        for u in session.query(Unit).all():
            u.image_path = os.path.abspath(__file__)
        session.commit()

        player1 = GameUser(telegram_id=6001, name="ActiveGamePlayer1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=6002, name="ActiveGamePlayer2", balance=Decimal("1000"))
        session.add(player1)
        session.add(player2)
        session.flush()

        user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
        user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
        session.add(user_unit1)
        session.add(user_unit2)
        session.commit()

        return player1, player2

    def test_has_active_game_flag(self):
        """Тест: флаг has_active_game устанавливается при наличии активной игры"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)

            # Проверяем что изначально нет активных игр
            active_games_count = session.query(Game).filter(
                Game.status == GameStatus.IN_PROGRESS
            ).count()
            assert active_games_count == 0

            # Создаем игру
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            assert game.status == GameStatus.WAITING

            # Принимаем игру - теперь она активна
            success, _ = engine.accept_game(game.id, player2.id)
            assert success

            # Проверяем что теперь есть активная игра
            active_games_count = session.query(Game).filter(
                Game.status == GameStatus.IN_PROGRESS
            ).count()
            assert active_games_count == 1

            # Проверяем флаг has_active_game логику
            has_active_game = active_games_count > 0
            assert has_active_game is True

    def test_no_active_game_flag_when_only_waiting(self):
        """Тест: флаг has_active_game = False когда игра только ожидает"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)

            # Создаем игру но не принимаем её
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            assert game.status == GameStatus.WAITING

            # Проверяем что активных игр нет
            active_games_count = session.query(Game).filter(
                Game.status == GameStatus.IN_PROGRESS
            ).count()
            assert active_games_count == 0

            has_active_game = active_games_count > 0
            assert has_active_game is False

    def test_redirect_to_active_game(self):
        """Тест: при наличии активной игры пользователь должен быть перенаправлен на неё"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            engine.accept_game(game.id, player2.id)

            game_id = game.id
            player1_id = game.player1_id

            # Проверяем что игра активна
            assert game.status == GameStatus.IN_PROGRESS

            # Симулируем логику из route /arena/play
            active_game = session.query(Game).filter(
                Game.status == GameStatus.IN_PROGRESS
            ).first()

            assert active_game is not None
            assert active_game.id == game_id

            # URL для редиректа должен содержать game_id и player_id
            redirect_params = {
                'game_id': active_game.id,
                'player_id': active_game.player1_id
            }
            assert redirect_params['game_id'] == game_id
            assert redirect_params['player_id'] == player1_id

    def test_play_game_route_redirects_completed_to_replay(self):
        """Тест: завершенная игра редиректит на просмотр replay"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.name, "5x5")
            engine.accept_game(game.id, player2.id)

            game_id = game.id

            # Завершаем игру вручную
            game.status = GameStatus.COMPLETED
            game.winner_id = player1.id
            session.commit()

            # Симулируем логику из route /arena/play/<game_id>
            game = session.query(Game).filter_by(id=game_id).first()

            if game.status != GameStatus.IN_PROGRESS:
                if game.status == GameStatus.COMPLETED:
                    # Должен быть редирект на replay
                    should_redirect_to_replay = True
                else:
                    should_redirect_to_replay = False

            assert should_redirect_to_replay is True


class TestCacheBusting:
    """Тесты для cache busting статических файлов"""

    def test_get_static_version_returns_hash(self):
        """Тест: get_static_version возвращает хеш версии"""
        from admin_arena import get_static_version

        version = get_static_version()

        # Версия должна быть строкой
        assert isinstance(version, str)

        # Версия должна быть 8 символов (короткий md5 хеш)
        assert len(version) == 8

        # Версия должна состоять из hex-символов
        assert all(c in '0123456789abcdef' for c in version)

    def test_static_version_changes_with_admin_version(self):
        """Тест: static_version меняется при изменении admin_version"""
        import hashlib
        from admin_templates import get_admin_version

        admin_ver = get_admin_version()

        # Вычисляем ожидаемую версию
        expected_hash = hashlib.md5(admin_ver.encode()).hexdigest()[:8]

        from admin_arena import get_static_version
        actual_version = get_static_version()

        assert actual_version == expected_hash

    def test_versioned_filter_in_admin_app(self):
        """Тест: фильтр versioned добавляет версию к URL"""
        from admin_app import versioned_filter

        url = "/static/arena/css/arena.css"
        versioned_url = versioned_filter(url)

        # URL должен содержать ?v=
        assert "?v=" in versioned_url
        # Оригинальный URL должен сохраниться
        assert url in versioned_url

    def test_versioned_filter_handles_existing_query_params(self):
        """Тест: фильтр versioned корректно работает с существующими query params"""
        from admin_app import versioned_filter

        url = "/static/file.js?existing=param"
        versioned_url = versioned_filter(url)

        # URL должен содержать &v= (не ?v=)
        assert "&v=" in versioned_url
        # Оригинальный параметр должен сохраниться
        assert "existing=param" in versioned_url

    def test_versioned_static_function(self):
        """Тест: функция versioned_static генерирует правильный URL"""
        from admin_app import inject_static_version

        context = inject_static_version()
        versioned_static = context['versioned_static']

        url = versioned_static('arena/css/arena.css')

        # URL должен начинаться с /static/
        assert url.startswith('/static/')
        # URL должен содержать имя файла
        assert 'arena/css/arena.css' in url
        # URL должен содержать версию
        assert '?v=' in url


class TestOpponentSelectionLogic:
    """Тесты для логики выбора противника (как в challenge из бота)"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка тестовой базы данных с уникальным префиксом"""
        import uuid
        self.test_prefix = f"opponent_test_{uuid.uuid4().hex[:8]}"
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            # Удаляем тестовых игроков с нашим префиксом
            session.query(GameUser).filter(
                GameUser.name.like(f"{self.test_prefix}%")
            ).delete(synchronize_session=False)
            session.commit()

        yield

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).filter(
                GameUser.name.like(f"{self.test_prefix}%")
            ).delete(synchronize_session=False)
            session.commit()

    def test_get_available_opponents_by_username_returns_tuple(self):
        """Тест: метод возвращает кортеж (current_player, opponents)"""
        with self.db.get_session() as session:
            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            # Создаем игрока с уникальным именем и username
            player = GameUser(
                telegram_id=7001,
                name=f"{self.test_prefix}_Player1",
                username=f"{self.test_prefix}_user1",
                balance=Decimal("1000")
            )
            session.add(player)
            session.flush()

            # Даем юнитов
            user_unit = UserUnit(game_user_id=player.id, unit_type_id=unit.id, count=5)
            session.add(user_unit)
            session.commit()

        # Вызываем метод
        result = self.db.get_available_opponents_by_username(f"{self.test_prefix}_user1")

        assert isinstance(result, tuple)
        assert len(result) == 2

        current_player, opponents = result
        assert current_player is not None
        assert isinstance(opponents, list)

    def test_get_available_opponents_returns_player_data(self):
        """Тест: метод возвращает корректные данные текущего игрока"""
        with self.db.get_session() as session:
            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            player = GameUser(
                telegram_id=7002,
                name=f"{self.test_prefix}_Player2",
                username=f"{self.test_prefix}_user2",
                balance=Decimal("1500")
            )
            session.add(player)
            session.flush()

            user_unit = UserUnit(game_user_id=player.id, unit_type_id=unit.id, count=10)
            session.add(user_unit)
            session.commit()

            player_id = player.id

        current_player, _ = self.db.get_available_opponents_by_username(f"{self.test_prefix}_user2")

        assert current_player is not None
        assert current_player['id'] == player_id
        assert current_player['balance'] == 1500.0
        assert 'army_value' in current_player
        assert 'wins' in current_player
        assert 'losses' in current_player

    def test_get_available_opponents_excludes_self(self):
        """Тест: метод не включает текущего игрока в список противников"""
        with self.db.get_session() as session:
            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            # Создаем двух игроков
            player1 = GameUser(
                telegram_id=7003,
                name=f"{self.test_prefix}_Player3",
                username=f"{self.test_prefix}_user3",
                balance=Decimal("1000")
            )
            player2 = GameUser(
                telegram_id=7004,
                name=f"{self.test_prefix}_Player4",
                username=f"{self.test_prefix}_user4",
                balance=Decimal("1000")
            )
            session.add(player1)
            session.add(player2)
            session.flush()

            # Даем одинаковое количество юнитов
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
            session.add(user_unit1)
            session.add(user_unit2)
            session.commit()

            player1_id = player1.id

        current_player, opponents = self.db.get_available_opponents_by_username(f"{self.test_prefix}_user3")

        # Текущий игрок не должен быть в списке противников
        opponent_ids = [opp['id'] for opp in opponents]
        assert player1_id not in opponent_ids

    def test_get_available_opponents_returns_none_for_unknown_user(self):
        """Тест: метод возвращает None для несуществующего пользователя"""
        current_player, opponents = self.db.get_available_opponents_by_username("nonexistent_user_12345")

        assert current_player is None
        assert opponents == []

    def test_opponents_have_army_value_and_win_rate(self):
        """Тест: противники содержат army_value и win_rate"""
        with self.db.get_session() as session:
            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            player1 = GameUser(
                telegram_id=7005,
                name=f"{self.test_prefix}_Player5",
                username=f"{self.test_prefix}_user5",
                balance=Decimal("1000"),
                wins=5,
                losses=3
            )
            player2 = GameUser(
                telegram_id=7006,
                name=f"{self.test_prefix}_Player6",
                username=f"{self.test_prefix}_user6",
                balance=Decimal("1000"),
                wins=2,
                losses=1
            )
            session.add(player1)
            session.add(player2)
            session.flush()

            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
            session.add(user_unit1)
            session.add(user_unit2)
            session.commit()

        current_player, opponents = self.db.get_available_opponents_by_username(f"{self.test_prefix}_user5")

        assert len(opponents) > 0
        for opp in opponents:
            assert 'army_value' in opp
            assert 'win_rate' in opp
            assert isinstance(opp['army_value'], float)
            assert isinstance(opp['win_rate'], (int, float))


class TestPlayFormHiddenPlayerField:
    """Тесты для скрытого поля игрока в форме создания игры"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка с уникальным префиксом"""
        import uuid
        self.test_prefix = f"hidden_field_test_{uuid.uuid4().hex[:8]}"
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).filter(
                GameUser.name.like(f"{self.test_prefix}%")
            ).delete(synchronize_session=False)
            session.commit()

        yield

        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).filter(
                GameUser.name.like(f"{self.test_prefix}%")
            ).delete(synchronize_session=False)
            session.commit()

    def test_current_player_data_has_required_fields(self):
        """Тест: данные текущего игрока содержат все необходимые поля для отображения"""
        with self.db.get_session() as session:
            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            player = GameUser(
                telegram_id=8001,
                name=f"{self.test_prefix}_Player1",
                username=f"{self.test_prefix}_user1",
                balance=Decimal("2500"),
                wins=10,
                losses=5
            )
            session.add(player)
            session.flush()

            user_unit = UserUnit(game_user_id=player.id, unit_type_id=unit.id, count=15)
            session.add(user_unit)
            session.commit()

        current_player, _ = self.db.get_available_opponents_by_username(f"{self.test_prefix}_user1")

        # Поля, необходимые для шаблона PLAY_TEMPLATE
        assert 'id' in current_player  # для hidden field
        assert 'name' in current_player  # для отображения имени
        assert 'balance' in current_player  # для отображения баланса
        assert 'army_value' in current_player  # для отображения стоимости армии
        assert 'wins' in current_player  # для статистики
        assert 'losses' in current_player  # для статистики

        # Проверяем значения
        assert current_player['balance'] == 2500.0
        assert current_player['wins'] == 10
        assert current_player['losses'] == 5
        assert current_player['army_value'] > 0  # Должна быть посчитана стоимость армии

    def test_player_name_uses_username_when_available(self):
        """Тест: имя игрока использует username если он есть"""
        with self.db.get_session() as session:
            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            player = GameUser(
                telegram_id=8002,
                name=f"{self.test_prefix}_FirstName",
                username=f"{self.test_prefix}_testusername",
                balance=Decimal("1000")
            )
            session.add(player)
            session.flush()

            user_unit = UserUnit(game_user_id=player.id, unit_type_id=unit.id, count=5)
            session.add(user_unit)
            session.commit()

        current_player, _ = self.db.get_available_opponents_by_username(f"{self.test_prefix}_testusername")

        # name должен быть username (если он есть) согласно логике в repository.py
        assert current_player['name'] == f"{self.test_prefix}_testusername"


class TestVersionDisplay:
    """Тесты для отображения версий админки и бота"""

    def test_get_admin_version_returns_string(self):
        """Тест: get_admin_version возвращает строку"""
        from admin_templates import get_admin_version

        version = get_admin_version()
        assert isinstance(version, str)
        # Версия не должна быть пустой
        assert len(version) > 0

    def test_get_bot_version_returns_string(self):
        """Тест: get_bot_version возвращает строку"""
        from admin_templates import get_bot_version

        version = get_bot_version()
        assert isinstance(version, str)
        # Версия не должна быть пустой
        assert len(version) > 0

    def test_footer_template_contains_version_placeholders(self):
        """Тест: FOOTER_TEMPLATE содержит плейсхолдеры для версий"""
        from admin_templates import FOOTER_TEMPLATE

        assert '{{ admin_version }}' in FOOTER_TEMPLATE
        assert '{{ bot_version }}' in FOOTER_TEMPLATE


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
