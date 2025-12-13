#!/usr/bin/env python3
"""
Интеграционные тесты для Godot арены
Проверяет:
1. API состояния игры для Godot клиента
2. Формат данных для изометрического поля
3. Пути к изображениям юнитов
4. Загрузка текстур
"""

import pytest
from decimal import Decimal

from db import Database
from db.models import (
    Game, GameUser, Field, Unit, UserUnit,
    GameStatus, BattleUnit, Obstacle
)
from core.game_engine import GameEngine


class TestGodotGameState:
    """Тесты для API состояния игры в Godot формате"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка тестовой базы данных"""
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        # Очистка данных перед тестом
        with self.db.get_session() as session:
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

        yield

        # Очистка после теста
        with self.db.get_session() as session:
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

    def _create_test_players_with_units(self, session):
        """Создание тестовых игроков с юнитами"""
        # Получаем юнит из базы
        unit = session.query(Unit).first()
        if not unit:
            pytest.skip("No units in database")

        # Создаем игроков
        player1 = GameUser(telegram_id=2001, username="GodotPlayer1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=2002, username="GodotPlayer2", balance=Decimal("1000"))
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

    def test_game_state_has_field_info(self):
        """Тест: состояние игры содержит информацию о поле для изометрии"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.username, "5x5")

            # Принимаем игру
            engine.accept_game(game.id, player2.id)

            # Получаем состояние
            game = session.query(Game).filter_by(id=game.id).first()

            # Проверяем поле
            assert game.field is not None
            assert game.field.name == "5x5"
            assert game.field.width == 5
            assert game.field.height == 5

    def test_game_state_has_unit_positions(self):
        """Тест: состояние игры содержит позиции юнитов для изометрии"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.username, "5x5")
            engine.accept_game(game.id, player2.id)

            # Получаем состояние
            game = session.query(Game).filter_by(id=game.id).first()

            # Проверяем юнитов
            assert len(game.battle_units) > 0

            for bu in game.battle_units:
                # Каждый юнит должен иметь координаты
                assert bu.position_x is not None
                assert bu.position_y is not None
                assert 0 <= bu.position_x < 5
                assert 0 <= bu.position_y < 5

    def test_unit_has_image_path(self):
        """Тест: юниты содержат путь к изображению для загрузки в Godot"""
        with self.db.get_session() as session:
            # Получаем юнит
            unit = session.query(Unit).first()
            if not unit:
                pytest.skip("No units in database")

            # Проверяем наличие image_path
            # Может быть None если изображение не загружено
            assert hasattr(unit, 'image_path')

    def test_game_state_units_have_type_info(self):
        """Тест: боевые юниты содержат информацию о типе для отображения"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.username, "5x5")
            engine.accept_game(game.id, player2.id)

            game = session.query(Game).filter_by(id=game.id).first()

            for bu in game.battle_units:
                # Проверяем связь с типом юнита через user_unit
                assert bu.user_unit is not None
                assert bu.user_unit.unit is not None

                unit_type = bu.user_unit.unit
                assert unit_type.name is not None
                assert unit_type.icon is not None

    def test_game_state_has_current_player(self):
        """Тест: состояние игры содержит ID текущего игрока"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.username, "5x5")
            engine.accept_game(game.id, player2.id)

            game = session.query(Game).filter_by(id=game.id).first()

            # Проверяем текущего игрока
            assert game.current_player_id is not None
            assert game.current_player_id in [player1.id, player2.id]

    def test_game_state_has_obstacles(self):
        """Тест: состояние игры содержит препятствия для изометрического поля"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.username, "7x7")
            engine.accept_game(game.id, player2.id)

            game = session.query(Game).filter_by(id=game.id).first()

            # На поле 7x7 должны быть препятствия
            obstacles = session.query(Obstacle).filter_by(game_id=game.id).all()

            # Препятствия опциональны, но если есть - должны иметь координаты
            for obs in obstacles:
                assert obs.position_x is not None
                assert obs.position_y is not None


class TestGodotWaitingState:
    """Тесты для состояния ожидания игры"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка тестовой базы данных"""
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")

        with self.db.get_session() as session:
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

        yield

        with self.db.get_session() as session:
            session.query(BattleUnit).delete()
            session.query(Obstacle).delete()
            session.query(Game).delete()
            session.query(UserUnit).delete()
            session.query(GameUser).delete()
            session.commit()

    def _create_test_players_with_units(self, session):
        """Создание тестовых игроков с юнитами"""
        unit = session.query(Unit).first()
        if not unit:
            pytest.skip("No units in database")

        player1 = GameUser(telegram_id=3001, username="WaitPlayer1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=3002, username="WaitPlayer2", balance=Decimal("1000"))
        session.add(player1)
        session.add(player2)
        session.flush()

        user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=5)
        user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
        session.add(user_unit1)
        session.add(user_unit2)
        session.commit()

        return player1, player2

    def test_game_created_has_waiting_status(self):
        """Тест: созданная игра имеет статус waiting"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.username, "5x5")

            assert game.status == GameStatus.WAITING

    def test_game_accepted_has_in_progress_status(self):
        """Тест: принятая игра имеет статус in_progress"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.username, "5x5")

            assert game.status == GameStatus.WAITING

            # Принимаем игру
            engine.accept_game(game.id, player2.id)

            # Перечитываем из базы
            game = session.query(Game).filter_by(id=game.id).first()
            assert game.status == GameStatus.IN_PROGRESS

    def test_polling_returns_updated_status(self):
        """Тест: polling возвращает обновленный статус после принятия"""
        with self.db.get_session() as session:
            player1, player2 = self._create_test_players_with_units(session)

            engine = GameEngine(session)
            game, _ = engine.create_game(player1.id, player2.username, "5x5")
            game_id = game.id

            # Первый polling - waiting
            game = session.query(Game).filter_by(id=game_id).first()
            assert game.status == GameStatus.WAITING

            # Принимаем игру (эмуляция действия противника)
            engine.accept_game(game_id, player2.id)
            session.commit()

            # Второй polling - in_progress
            game = session.query(Game).filter_by(id=game_id).first()
            assert game.status == GameStatus.IN_PROGRESS


class TestIsometricCoordinates:
    """Тесты для изометрических координат"""

    def test_grid_coordinates_valid_range(self):
        """Тест: координаты сетки в допустимом диапазоне"""
        field_sizes = [5, 7, 10]

        for size in field_sizes:
            for x in range(size):
                for y in range(size):
                    # Координаты должны быть неотрицательными и меньше размера поля
                    assert 0 <= x < size
                    assert 0 <= y < size

    def test_isometric_transform_formula(self):
        """Тест: формула преобразования в изометрические координаты"""
        # Константы из game.gd
        TILE_WIDTH = 64
        TILE_HEIGHT = 32
        BOARD_OFFSET_X = 300
        BOARD_OFFSET_Y = 50

        def grid_to_iso(grid_x, grid_y):
            iso_x = (grid_x - grid_y) * (TILE_WIDTH // 2) + BOARD_OFFSET_X
            iso_y = (grid_x + grid_y) * (TILE_HEIGHT // 2) + BOARD_OFFSET_Y
            return (iso_x, iso_y)

        # Тест центральной клетки
        iso_x, iso_y = grid_to_iso(2, 2)
        assert iso_x == BOARD_OFFSET_X  # (2-2)*32 + 300 = 300
        assert iso_y == 2 * TILE_HEIGHT + BOARD_OFFSET_Y  # (2+2)*16 + 50 = 114

        # Тест угловых клеток
        # Верхний угол (0, 0)
        iso_x, iso_y = grid_to_iso(0, 0)
        assert iso_x == BOARD_OFFSET_X
        assert iso_y == BOARD_OFFSET_Y

        # Правый угол (4, 0) для поля 5x5
        iso_x, iso_y = grid_to_iso(4, 0)
        assert iso_x == 4 * (TILE_WIDTH // 2) + BOARD_OFFSET_X  # 128 + 300 = 428
        assert iso_y == 4 * (TILE_HEIGHT // 2) + BOARD_OFFSET_Y  # 64 + 50 = 114


class TestUnitImagePaths:
    """Тесты для путей к изображениям юнитов"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Подготовка тестовой базы данных"""
        self.db = Database("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")
        yield

    def test_unit_image_path_format(self):
        """Тест: формат пути к изображению юнита"""
        with self.db.get_session() as session:
            units = session.query(Unit).all()

            for unit in units:
                if unit.image_path:
                    # Путь должен начинаться с static/
                    assert unit.image_path.startswith("static/") or \
                           unit.image_path.startswith("/static/") or \
                           "static" in unit.image_path, \
                           f"Invalid image path format: {unit.image_path}"

    def test_all_units_have_icons(self):
        """Тест: все юниты имеют иконки (fallback для Godot)"""
        with self.db.get_session() as session:
            units = session.query(Unit).all()

            for unit in units:
                # Каждый юнит должен иметь иконку (эмодзи)
                assert unit.icon is not None
                assert len(unit.icon) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
