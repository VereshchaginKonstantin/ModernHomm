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
            player1 = GameUser(telegram_id=111, name="Player1", balance=1000)
            player2 = GameUser(telegram_id=222, name="Player2", balance=1000)
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
            # Сохраняем game_id до commit
            game_id_value = game.id

        # Проверяем в новой сессии
        with self.db.get_session() as session:
            log = session.query(GameLog).filter_by(id=log.id).first()
            assert log.game_id == game_id_value

    def test_create_game_log(self):
        """Тест: создание записи в логе игры"""
        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            player1 = GameUser(telegram_id=333, name="LogPlayer1", balance=1000)
            player2 = GameUser(telegram_id=444, name="LogPlayer2", balance=1000)
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

            player1 = GameUser(telegram_id=555, name="EventPlayer1", balance=1000)
            player2 = GameUser(telegram_id=666, name="EventPlayer2", balance=1000)
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

            player1 = GameUser(telegram_id=777, name="TimePlayer1", balance=1000)
            player2 = GameUser(telegram_id=888, name="TimePlayer2", balance=1000)
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

            player1 = GameUser(telegram_id=999, name="MultiLogPlayer1", balance=1000)
            player2 = GameUser(telegram_id=1000, name="MultiLogPlayer2", balance=1000)
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

            player1 = GameUser(telegram_id=1001, name="OrderPlayer1", balance=1000)
            player2 = GameUser(telegram_id=1002, name="OrderPlayer2", balance=1000)
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

            player1 = GameUser(telegram_id=1003, name="RelPlayer1", balance=1000)
            player2 = GameUser(telegram_id=1004, name="RelPlayer2", balance=1000)
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
            assert log.game.player1.name == "RelPlayer1"
            assert log.game.player2.name == "RelPlayer2"

    def test_delete_game_cascades_to_logs(self):
        """Тест: удаление игры каскадно удаляет логи"""
        with self.db.get_session() as session:
            field = session.query(Field).first()
            if not field:
                pytest.skip("No fields in database")

            player1 = GameUser(telegram_id=1005, name="CascadePlayer1", balance=1000)
            player2 = GameUser(telegram_id=1006, name="CascadePlayer2", balance=1000)
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
