#!/usr/bin/env python3
"""
Интеграционные тесты для функционала логирования игр (game_logs)
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from db import Database
from db.models import Game, GameUser, Field, GameLog, Unit, UserUnit, GameStatus


class TestGameLogs:
    """Тесты для функционала логирования игр"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка тестовой базы данных"""
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        # Очистка данных перед тестом
        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

        yield

        # Очистка после теста
        with self.db.get_session() as session:
            session.query(GameLog).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

    def test_game_logs_table_exists(self):
        """Тест: таблица game_logs существует"""
        with self.db.get_session() as session:
            # Получаем поле для создания игры
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            # Создаем игроков
            player1 = GameUser(telegram_id=111, username="Player1", balance=1000)
            player2 = GameUser(telegram_id=222, username="Player2", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            # Создаем игру
            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS.value
            )
            session.add(game)
            session.flush()

            # Создаем лог
            log = GameLog(
                game_id=game.id,
                event_type="game_start",
                message="Игра началась"
            )
            session.add(log)
            session.commit()

            # Проверяем, что лог создан
            assert log.id is not None
            # Сохраняем значения до выхода из сессии
            log_id_value = log.id
            game_id_value = game.id

        # Проверяем в новой сессии
        with self.db.get_session() as session:
            log = session.query(GameLog).filter_by(id=log_id_value).first()
            assert log.game_id == game_id_value

    def test_create_game_log(self):
        """Тест: создание записи в логе игры"""
        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            player1 = GameUser(telegram_id=333, username="LogPlayer1", balance=1000)
            player2 = GameUser(telegram_id=444, username="LogPlayer2", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS.value
            )
            session.add(game)
            session.flush()

            # Создаем лог атаки
            log = GameLog(
                game_id=game.id,
                event_type="attack",
                message="Игрок LogPlayer1 атаковал LogPlayer2"
            )
            session.add(log)
            session.commit()
            log_id = log.id

        # Проверяем, что лог сохранен
        with self.db.get_session() as session:
            log = session.query(GameLog).filter_by(id=log_id).first()
            assert log is not None
            assert log.event_type == "attack"
            assert "атаковал" in log.message

    def test_game_log_event_types(self):
        """Тест: различные типы событий в логе"""
        event_types = [
            ("game_start", "Игра началась"),
            ("move", "Юнит переместился"),
            ("attack", "Атака произошла"),
            ("damage", "Нанесен урон"),
            ("dodge", "Уклонение от атаки"),
            ("crit", "Критический удар"),
            ("end_turn", "Ход завершен"),
            ("game_end", "Игра завершена"),
        ]

        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            player1 = GameUser(telegram_id=555, username="EventPlayer1", balance=1000)
            player2 = GameUser(telegram_id=666, username="EventPlayer2", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS.value
            )
            session.add(game)
            session.flush()
            game_id = game.id

            # Создаем логи для всех типов событий
            for event_type, message in event_types:
                log = GameLog(
                    game_id=game_id,
                    event_type=event_type,
                    message=message
                )
                session.add(log)
            session.commit()

        # Проверяем, что все логи созданы
        with self.db.get_session() as session:
            logs = session.query(GameLog).filter_by(game_id=game_id).all()
            assert len(logs) == len(event_types)

            # Проверяем, что все типы событий присутствуют
            log_event_types = [log.event_type for log in logs]
            for event_type, _ in event_types:
                assert event_type in log_event_types

    def test_game_log_created_at(self):
        """Тест: автоматическая установка времени created_at"""
        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            player1 = GameUser(telegram_id=777, username="TimePlayer1", balance=1000)
            player2 = GameUser(telegram_id=888, username="TimePlayer2", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS.value
            )
            session.add(game)
            session.flush()

            before_time = datetime.utcnow()
            log = GameLog(
                game_id=game.id,
                event_type="test",
                message="Тест времени"
            )
            session.add(log)
            session.commit()
            after_time = datetime.utcnow()

            # Проверяем, что created_at установлен автоматически
            assert log.created_at is not None
            # Время должно быть между before_time и after_time
            assert before_time <= log.created_at <= after_time

    def test_multiple_logs_for_game(self):
        """Тест: несколько логов для одной игры"""
        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            player1 = GameUser(telegram_id=999, username="MultiLogPlayer1", balance=1000)
            player2 = GameUser(telegram_id=1000, username="MultiLogPlayer2", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS.value
            )
            session.add(game)
            session.flush()
            game_id = game.id

            # Создаем 10 логов для одной игры
            for i in range(10):
                log = GameLog(
                    game_id=game_id,
                    event_type="move",
                    message=f"Ход {i + 1}"
                )
                session.add(log)
            session.commit()

        # Проверяем количество логов
        with self.db.get_session() as session:
            logs = session.query(GameLog).filter_by(game_id=game_id).all()
            assert len(logs) == 10

    def test_game_log_ordering_by_time(self):
        """Тест: упорядочивание логов по времени"""
        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            player1 = GameUser(telegram_id=1001, username="OrderPlayer1", balance=1000)
            player2 = GameUser(telegram_id=1002, username="OrderPlayer2", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS.value
            )
            session.add(game)
            session.flush()
            game_id = game.id

            # Создаем логи с небольшой задержкой
            messages = ["Начало игры", "Первый ход", "Второй ход", "Конец игры"]
            for i, message in enumerate(messages):
                log = GameLog(
                    game_id=game_id,
                    event_type="move",
                    message=message
                )
                session.add(log)
                session.flush()
            session.commit()

        # Проверяем упорядочивание
        with self.db.get_session() as session:
            logs = session.query(GameLog).filter_by(game_id=game_id).order_by(GameLog.created_at).all()

            # Проверяем, что логи упорядочены по времени
            for i in range(len(logs) - 1):
                assert logs[i].created_at <= logs[i + 1].created_at

            # Проверяем порядок сообщений
            log_messages = [log.message for log in logs]
            assert log_messages == messages

    def test_game_log_relationship_with_game(self):
        """Тест: связь между логом и игрой"""
        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            player1 = GameUser(telegram_id=1003, username="RelPlayer1", balance=1000)
            player2 = GameUser(telegram_id=1004, username="RelPlayer2", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS.value
            )
            session.add(game)
            session.flush()

            log = GameLog(
                game_id=game.id,
                event_type="test",
                message="Тест связи"
            )
            session.add(log)
            session.commit()
            log_id = log.id

        # Проверяем связь через relationship
        with self.db.get_session() as session:
            log = session.query(GameLog).filter_by(id=log_id).first()
            assert log.game is not None
            assert log.game.player1.username == "RelPlayer1"
            assert log.game.player2.username == "RelPlayer2"

    def test_delete_game_cascades_to_logs(self):
        """Тест: удаление игры каскадно удаляет логи"""
        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            player1 = GameUser(telegram_id=1005, username="CascadePlayer1", balance=1000)
            player2 = GameUser(telegram_id=1006, username="CascadePlayer2", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS.value
            )
            session.add(game)
            session.flush()
            game_id = game.id

            # Создаем несколько логов
            for i in range(5):
                log = GameLog(
                    game_id=game_id,
                    event_type="test",
                    message=f"Лог {i}"
                )
                session.add(log)
            session.commit()

        # Проверяем, что логи созданы
        with self.db.get_session() as session:
            logs = session.query(GameLog).filter_by(game_id=game_id).all()
            assert len(logs) == 5

            # Удаляем игру
            game = session.query(Game).filter_by(id=game_id).first()
            session.delete(game)
            session.commit()

        # Проверяем, что логи удалены каскадно
        with self.db.get_session() as session:
            logs = session.query(GameLog).filter_by(game_id=game_id).all()
            assert len(logs) == 0


class TestTurnSwitchLogging:
    """Тесты для логирования смены хода"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка тестовой базы данных"""
        import os
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        # Создаём тестовый файл изображения
        self.test_image_path = "/tmp/test_unit_image_logs.png"
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        with open(self.test_image_path, 'wb') as f:
            f.write(png_data)

        # Очистка данных перед тестом
        with self.db.get_session() as session:
            from db.models import BattleUnit
            from sqlalchemy import text
            session.query(BattleUnit).delete()
            session.query(GameLog).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            # Обновляем пути к изображениям для всех юнитов
            session.execute(text(f"UPDATE units SET image_path = '{self.test_image_path}'"))
            session.commit()

        yield

        # Удаляем тестовый файл изображения
        if os.path.exists(self.test_image_path):
            os.unlink(self.test_image_path)

        # Очистка после теста
        with self.db.get_session() as session:
            from db.models import BattleUnit
            session.query(BattleUnit).delete()
            session.query(GameLog).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

    def test_turn_switch_creates_log_entry(self):
        """Тест: смена хода создает запись в логе с типом turn_switch"""
        from core.game_engine import GameEngine

        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            # Создаем игроков
            player1 = GameUser(telegram_id=2001, username="turnplayer1", balance=1000)
            player2 = GameUser(telegram_id=2002, username="turnplayer2", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            # Создаем юнитов для игроков
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
            session.add(user_unit1)
            session.add(user_unit2)
            session.commit()

            # Создаем игру через GameEngine
            engine = GameEngine(session)
            game, message = engine.create_game(player1.id, "turnplayer2")
            game_id = game.id

            # Принимаем игру
            engine.accept_game(game_id, player2.id)

            # Получаем юнита для хода
            from db.models import BattleUnit
            battle_units = session.query(BattleUnit).filter_by(
                game_id=game_id,
                player_id=player1.id
            ).all()

            # Пропускаем ходы всех юнитов первого игрока, чтобы сменился ход
            for bu in battle_units:
                engine.skip_unit_turn(game_id, player1.id, bu.id)

        # Проверяем, что создана запись в логе о смене хода
        with self.db.get_session() as session:
            turn_switch_logs = session.query(GameLog).filter_by(
                game_id=game_id,
                event_type="turn_switch"
            ).all()

            assert len(turn_switch_logs) > 0, "Должна быть хотя бы одна запись о смене хода"

            # Проверяем формат сообщения
            latest_log = turn_switch_logs[-1]
            assert "🔄 Ход переходит к" in latest_log.message
            assert "TurnPlayer2" in latest_log.message or "turnplayer2" in latest_log.message

    def test_turn_switch_log_contains_player_name(self):
        """Тест: лог смены хода содержит имя игрока, к которому переходит ход"""
        from core.game_engine import GameEngine

        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            # Создаем игроков с уникальными именами
            player1 = GameUser(telegram_id=2003, username="alpha_user", balance=1000)
            player2 = GameUser(telegram_id=2004, username="beta_user", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            # Создаем юнитов
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
            session.add(user_unit1)
            session.add(user_unit2)
            session.commit()

            # Создаем игру
            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, "beta_user")
            game_id = game.id

            # Принимаем игру
            engine.accept_game(game_id, player2.id)

            # Пропускаем все ходы первого игрока
            from db.models import BattleUnit
            battle_units = session.query(BattleUnit).filter_by(
                game_id=game_id,
                player_id=player1.id
            ).all()

            for bu in battle_units:
                engine.skip_unit_turn(game_id, player1.id, bu.id)

        # Проверяем содержимое лога
        with self.db.get_session() as session:
            turn_log = session.query(GameLog).filter_by(
                game_id=game_id,
                event_type="turn_switch"
            ).order_by(GameLog.created_at.desc()).first()

            assert turn_log is not None
            # Должно содержать username или name игрока 2
            assert "beta_user" in turn_log.message or "Бета" in turn_log.message

    def test_turn_switch_log_event_type(self):
        """Тест: event_type для смены хода должен быть 'turn_switch'"""
        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            # Создаем тестовую запись лога напрямую
            player1 = GameUser(telegram_id=2005, username="TestP1", balance=1000)
            player2 = GameUser(telegram_id=2006, username="TestP2", balance=1000)
            session.add(player1)
            session.add(player2)
            session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS.value
            )
            session.add(game)
            session.flush()

            # Создаем лог смены хода
            log = GameLog(
                game_id=game.id,
                event_type="turn_switch",
                message="🔄 Ход переходит к TestP2"
            )
            session.add(log)
            session.commit()
            log_id = log.id

        # Проверяем
        with self.db.get_session() as session:
            log = session.query(GameLog).filter_by(id=log_id).first()
            assert log.event_type == "turn_switch"
            assert "🔄" in log.message


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
