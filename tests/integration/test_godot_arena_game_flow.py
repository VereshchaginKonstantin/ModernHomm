#!/usr/bin/env python3
"""
Интеграционные тесты для полного игрового цикла Godot Arena.

Тесты работают с production базой данных (порт 5434) и проверяют:
1. Создание пользователей и армий через БД
2. Создание игры через Godot Arena API
3. Принятие игры через API
4. Получение состояния игры с юнитами и полем
5. Выполнение ходов и атак
6. Проверка загрузки текстур юнитов
"""

import os
import random
import pytest
import requests
import hashlib
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

from db.models import (
    Base, GameRace, RaceUnit, RaceUnitSkin, UnitLevel,
    GameUser, UserRace, UserRaceUnit, Army, ArmyUnit,
    Game, BattleUnit, GameStatus, Field
)


# Production database URL (порт 5434)
PROD_DATABASE_URL = os.getenv('PROD_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')

# API Base URL
API_BASE_URL = os.getenv('API_BASE_URL', 'https://localhost')

# Disable SSL warnings for localhost
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TestGodotArenaGameFlow:
    """Интеграционные тесты полного игрового цикла."""

    @pytest.fixture
    def prod_db_session(self):
        """Сессия к production базе данных."""
        engine = create_engine(PROD_DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_users_and_armies(self, prod_db_session):
        """
        Создаёт двух тестовых пользователей с армиями.
        Использует существующую расу "Люди" (id=13) и её юнитов.
        """
        session = prod_db_session

        # Генерируем уникальные имена для тестовых пользователей
        suffix = random.randint(100000, 999999)
        user1_name = f"test_arena_player1_{suffix}"
        user2_name = f"test_arena_player2_{suffix}"
        password = "testpass123"
        password_hash = generate_password_hash(password)

        # Получаем существующую расу "Люди"
        race = session.query(GameRace).filter_by(name="Люди").first()
        if not race:
            pytest.skip("Раса 'Люди' не найдена в базе данных")

        # Получаем юнитов расы для армии
        race_units = session.query(RaceUnit).filter_by(race_id=race.id).all()
        if len(race_units) < 2:
            pytest.skip("Недостаточно юнитов расы для тестов")

        # Создаём пользователя 1
        user1 = GameUser(
            telegram_id=random.randint(100000000, 999999999),
            username=user1_name,
            balance=Decimal("10000.00"),
            glory=1000,
            password_hash=password_hash
        )
        session.add(user1)
        session.flush()

        # Создаём пользователя 2
        user2 = GameUser(
            telegram_id=random.randint(100000000, 999999999),
            username=user2_name,
            balance=Decimal("10000.00"),
            glory=1000,
            password_hash=password_hash
        )
        session.add(user2)
        session.flush()

        # Создаём UserRace для обоих пользователей
        user_race1 = UserRace(user_id=user1.id, race_id=race.id)
        user_race2 = UserRace(user_id=user2.id, race_id=race.id)
        session.add(user_race1)
        session.add(user_race2)
        session.flush()

        # Создаём армии для обоих пользователей
        army1 = Army(
            user_race_id=user_race1.id,
            name=f"Test Army 1 {suffix}"
        )
        army2 = Army(
            user_race_id=user_race2.id,
            name=f"Test Army 2 {suffix}"
        )
        session.add(army1)
        session.add(army2)
        session.flush()

        # Добавляем юнитов в армии (по 2 типа юнитов, по 3 штуки каждого)
        for i, race_unit in enumerate(race_units[:3]):
            army_unit1 = ArmyUnit(
                army_id=army1.id,
                race_unit_id=race_unit.id,
                count=3
            )
            army_unit2 = ArmyUnit(
                army_id=army2.id,
                race_unit_id=race_unit.id,
                count=3
            )
            session.add(army_unit1)
            session.add(army_unit2)

        session.commit()

        yield {
            'user1': user1,
            'user2': user2,
            'user1_name': user1_name,
            'user2_name': user2_name,
            'password': password,
            'army1': army1,
            'army2': army2,
            'race': race,
            'race_units': race_units
        }

        # Cleanup после теста
        try:
            # Удаляем игры
            session.query(BattleUnit).filter(
                BattleUnit.game_id.in_(
                    session.query(Game.id).filter(
                        (Game.player1_id == user1.id) | (Game.player2_id == user1.id)
                    )
                )
            ).delete(synchronize_session=False)
            session.query(Game).filter(
                (Game.player1_id == user1.id) | (Game.player2_id == user1.id)
            ).delete(synchronize_session=False)

            # Удаляем армии
            session.query(ArmyUnit).filter(ArmyUnit.army_id == army1.id).delete()
            session.query(ArmyUnit).filter(ArmyUnit.army_id == army2.id).delete()
            session.query(Army).filter(Army.id == army1.id).delete()
            session.query(Army).filter(Army.id == army2.id).delete()

            # Удаляем user races
            session.query(UserRace).filter(UserRace.id == user_race1.id).delete()
            session.query(UserRace).filter(UserRace.id == user_race2.id).delete()

            # Удаляем пользователей
            session.query(GameUser).filter(GameUser.id == user1.id).delete()
            session.query(GameUser).filter(GameUser.id == user2.id).delete()

            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Cleanup error: {e}")

    def _login(self, username: str, password: str) -> dict:
        """Логин через API и получение токена."""
        response = requests.post(
            f"{API_BASE_URL}/arena/api/public/login",
            json={"username": username, "password": password},
            verify=False
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()

    def _get_headers(self, token: str) -> dict:
        """Получить заголовки с авторизацией."""
        return {"Authorization": f"Bearer {token}"}

    def test_full_game_flow(self, test_users_and_armies):
        """
        Полный тест игрового цикла:
        1. Логин обоих пользователей
        2. Создание игры от пользователя 1
        3. Проверка pending games для пользователя 2
        4. Принятие игры пользователем 2
        5. Проверка состояния игры (поле, юниты)
        6. Выполнение нескольких ходов
        7. Проверка обновления состояния
        """
        data = test_users_and_armies

        # === Шаг 1: Логин обоих пользователей ===
        login1 = self._login(data['user1_name'], data['password'])
        assert 'token' in login1, "Токен не получен для пользователя 1"
        token1 = login1['token']
        player1_id = login1['player']['id']

        login2 = self._login(data['user2_name'], data['password'])
        assert 'token' in login2, "Токен не получен для пользователя 2"
        token2 = login2['token']
        player2_id = login2['player']['id']

        # === Шаг 2: Создание игры от пользователя 1 ===
        create_response = requests.post(
            f"{API_BASE_URL}/arena/api/public/games/create",
            json={
                "player2_name": data['user2_name'],
                "field_size": "5x5",
                "army_id": data['army1'].id
            },
            headers=self._get_headers(token1),
            verify=False
        )
        assert create_response.status_code == 200, f"Game creation failed: {create_response.text}"
        game_data = create_response.json()
        assert 'game_id' in game_data, "game_id не получен"
        game_id = game_data['game_id']

        # === Шаг 3: Проверка pending games для пользователя 2 ===
        pending_response = requests.get(
            f"{API_BASE_URL}/arena/api/public/games/pending",
            headers=self._get_headers(token2),
            verify=False
        )
        assert pending_response.status_code == 200, f"Pending games failed: {pending_response.text}"
        pending_data = pending_response.json()

        pending_games = pending_data.get('pending_games', [])
        assert len(pending_games) > 0, "Нет ожидающих игр для пользователя 2"

        # Находим нашу игру
        our_game = None
        for g in pending_games:
            if g.get('game_id') == game_id:
                our_game = g
                break
        assert our_game is not None, f"Игра {game_id} не найдена в pending games"
        assert our_game['player1_name'] == data['user1_name'], "Неверное имя player1"

        # === Шаг 4: Принятие игры пользователем 2 ===
        accept_response = requests.post(
            f"{API_BASE_URL}/arena/api/public/games/{game_id}/accept",
            json={"army_id": data['army2'].id},
            headers=self._get_headers(token2),
            verify=False
        )
        assert accept_response.status_code == 200, f"Game accept failed: {accept_response.text}"
        accept_data = accept_response.json()
        assert accept_data.get('status') == 'in_progress', "Игра не перешла в статус in_progress"

        # === Шаг 5: Проверка состояния игры ===
        state_response = requests.get(
            f"{API_BASE_URL}/arena/api/public/games/{game_id}/state",
            headers=self._get_headers(token1),
            verify=False
        )
        assert state_response.status_code == 200, f"Game state failed: {state_response.text}"
        game_state = state_response.json()

        # Проверяем структуру состояния игры
        assert game_state.get('game_id') == game_id, "Неверный game_id"
        assert game_state.get('status') == 'in_progress', "Неверный статус игры"
        assert 'field' in game_state, "Нет информации о поле"
        assert 'units' in game_state, "Нет информации о юнитах"

        # Проверяем поле (размер определяется динамически)
        field = game_state['field']
        assert field.get('width') in [5, 7, 10], f"Неверная ширина поля: {field.get('width')}"
        assert field.get('height') in [5, 7, 10], f"Неверная высота поля: {field.get('height')}"
        assert field.get('width') == field.get('height'), "Поле должно быть квадратным"

        # Проверяем юнитов
        units = game_state['units']
        assert len(units) > 0, "Юниты не созданы"

        # Проверяем что у каждого юнита есть нужные поля
        for unit in units:
            assert 'id' in unit, "Юнит без id"
            assert 'player_id' in unit, "Юнит без player_id"
            assert 'x' in unit, "Юнит без координаты x"
            assert 'y' in unit, "Юнит без координаты y"
            assert 'count' in unit, "Юнит без count"
            assert 'unit_type' in unit, "Юнит без unit_type"

            unit_type = unit['unit_type']
            assert 'name' in unit_type, "unit_type без name"
            assert 'icon' in unit_type, "unit_type без icon"

        # Проверяем что есть юниты обоих игроков
        player1_units = [u for u in units if u['player_id'] == player1_id]
        player2_units = [u for u in units if u['player_id'] == player2_id]
        assert len(player1_units) > 0, "Нет юнитов игрока 1"
        assert len(player2_units) > 0, "Нет юнитов игрока 2"

        # === Шаг 6: Проверка текстур юнитов ===
        for unit in units[:2]:  # Проверяем первые 2 юнита
            unit_type = unit['unit_type']
            if unit_type.get('image_url'):
                image_url = f"{API_BASE_URL}{unit_type['image_url']}"
                img_response = requests.get(image_url, verify=False)
                # Текстура должна загружаться (200) или возвращать 404 если нет изображения
                assert img_response.status_code in [200, 404], \
                    f"Ошибка загрузки текстуры: {img_response.status_code}"

        # === Шаг 7: Получение доступных действий для юнита ===
        current_player_id = game_state.get('current_player_id')
        current_token = token1 if current_player_id == player1_id else token2

        # Находим юнита текущего игрока
        current_units = player1_units if current_player_id == player1_id else player2_units
        if current_units:
            test_unit = current_units[0]

            actions_response = requests.get(
                f"{API_BASE_URL}/arena/api/public/games/{game_id}/units/{test_unit['id']}/actions",
                headers=self._get_headers(current_token),
                verify=False
            )
            assert actions_response.status_code == 200, f"Unit actions failed: {actions_response.text}"
            actions = actions_response.json()

            assert 'moves' in actions, "Нет списка moves"
            assert 'attacks' in actions, "Нет списка attacks"

            # === Шаг 8: Выполнение хода (если есть доступные клетки) ===
            moves = actions.get('moves', [])
            if moves:
                target_move = random.choice(moves)
                move_response = requests.post(
                    f"{API_BASE_URL}/arena/api/public/games/{game_id}/move",
                    json={
                        "unit_id": test_unit['id'],
                        "action": "move",
                        "target_x": target_move['x'],
                        "target_y": target_move['y']
                    },
                    headers=self._get_headers(current_token),
                    verify=False
                )
                assert move_response.status_code == 200, f"Move failed: {move_response.text}"
                move_result = move_response.json()
                assert move_result.get('success') == True, "Ход не выполнен"

                # Проверяем обновлённое состояние
                new_state = move_result.get('game_state', {})
                if new_state:
                    # Находим перемещённого юнита
                    moved_unit = None
                    for u in new_state.get('units', []):
                        if u['id'] == test_unit['id']:
                            moved_unit = u
                            break

                    if moved_unit:
                        assert moved_unit['x'] == target_move['x'], "Юнит не переместился по X"
                        assert moved_unit['y'] == target_move['y'], "Юнит не переместился по Y"

    def test_game_state_has_all_required_fields(self, test_users_and_armies):
        """Тест что состояние игры содержит все необходимые поля для Godot клиента."""
        data = test_users_and_armies

        # Логин и создание игры
        login1 = self._login(data['user1_name'], data['password'])
        token1 = login1['token']

        login2 = self._login(data['user2_name'], data['password'])
        token2 = login2['token']

        # Создаём игру
        create_response = requests.post(
            f"{API_BASE_URL}/arena/api/public/games/create",
            json={
                "player2_name": data['user2_name'],
                "field_size": "7x7",
                "army_id": data['army1'].id
            },
            headers=self._get_headers(token1),
            verify=False
        )
        game_id = create_response.json()['game_id']

        # Принимаем игру
        requests.post(
            f"{API_BASE_URL}/arena/api/public/games/{game_id}/accept",
            json={"army_id": data['army2'].id},
            headers=self._get_headers(token2),
            verify=False
        )

        # Получаем состояние
        state_response = requests.get(
            f"{API_BASE_URL}/arena/api/public/games/{game_id}/state",
            headers=self._get_headers(token1),
            verify=False
        )
        game_state = state_response.json()

        # Проверяем все обязательные поля для Godot клиента
        required_fields = [
            'game_id', 'status', 'field', 'player1_id', 'player1_name',
            'player2_id', 'player2_name', 'current_player_id', 'is_game_over',
            'units', 'obstacles', 'logs'
        ]

        for field in required_fields:
            assert field in game_state, f"Отсутствует обязательное поле: {field}"

        # Проверяем структуру field
        field = game_state['field']
        assert 'name' in field, "field без name"
        assert 'width' in field, "field без width"
        assert 'height' in field, "field без height"

        # Проверяем структуру units
        for unit in game_state['units']:
            unit_required = ['id', 'player_id', 'x', 'y', 'count', 'has_moved', 'unit_type']
            for f in unit_required:
                assert f in unit, f"unit без поля {f}"

            unit_type = unit['unit_type']
            unit_type_required = ['id', 'name', 'icon', 'attack', 'defense', 'hp', 'speed']
            for f in unit_type_required:
                assert f in unit_type, f"unit_type без поля {f}"

    def test_hint_label_bug_fixed(self, test_users_and_armies):
        """
        Тест что баг с hint_label исправлен.
        Проверяем что после получения game_state клиент может отобразить состояние игры.
        """
        data = test_users_and_armies

        # Логин и создание игры
        login1 = self._login(data['user1_name'], data['password'])
        token1 = login1['token']
        player1_id = login1['player']['id']

        login2 = self._login(data['user2_name'], data['password'])
        token2 = login2['token']

        # Создаём игру
        create_response = requests.post(
            f"{API_BASE_URL}/arena/api/public/games/create",
            json={
                "player2_name": data['user2_name'],
                "field_size": "5x5",
                "army_id": data['army1'].id
            },
            headers=self._get_headers(token1),
            verify=False
        )
        game_id = create_response.json()['game_id']

        # Принимаем игру
        requests.post(
            f"{API_BASE_URL}/arena/api/public/games/{game_id}/accept",
            json={"army_id": data['army2'].id},
            headers=self._get_headers(token2),
            verify=False
        )

        # Получаем состояние
        state_response = requests.get(
            f"{API_BASE_URL}/arena/api/public/games/{game_id}/state",
            headers=self._get_headers(token1),
            verify=False
        )
        assert state_response.status_code == 200
        game_state = state_response.json()

        # Проверяем что состояние не пустое (это было причиной "зависания")
        assert game_state, "Состояние игры пустое"
        assert game_state.get('status') == 'in_progress', "Игра должна быть in_progress"

        # Проверяем что есть юниты (иначе поле будет выглядеть пустым)
        units = game_state.get('units', [])
        assert len(units) > 0, "Нет юнитов в игре - поле будет пустым!"

        # Проверяем что current_player_id установлен (для определения чей ход)
        assert game_state.get('current_player_id') is not None, \
            "current_player_id не установлен - hint_label не сможет показать чей ход"

        # Проверяем что field корректно распарсится
        field = game_state.get('field', {})
        field_name = field.get('name', '')
        assert 'x' in field_name, f"Некорректное имя поля: {field_name}"


class TestGodotArenaMovement:
    """Тесты для проверки механики перемещения."""

    @pytest.fixture
    def prod_db_session(self):
        """Сессия к production базе данных."""
        engine = create_engine(PROD_DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_game_in_progress(self, prod_db_session):
        """Создаёт готовую игру в статусе in_progress для тестов движения."""
        session = prod_db_session

        suffix = random.randint(100000, 999999)
        user1_name = f"move_test_p1_{suffix}"
        user2_name = f"move_test_p2_{suffix}"
        password = "testpass123"
        password_hash = generate_password_hash(password)

        race = session.query(GameRace).filter_by(name="Люди").first()
        if not race:
            pytest.skip("Раса 'Люди' не найдена")

        race_units = session.query(RaceUnit).filter_by(race_id=race.id).all()
        if not race_units:
            pytest.skip("Нет юнитов расы")

        # Создаём пользователей
        user1 = GameUser(
            telegram_id=random.randint(100000000, 999999999),
            username=user1_name,
            balance=Decimal("10000.00"),
            glory=1000,
            password_hash=password_hash
        )
        user2 = GameUser(
            telegram_id=random.randint(100000000, 999999999),
            username=user2_name,
            balance=Decimal("10000.00"),
            glory=1000,
            password_hash=password_hash
        )
        session.add_all([user1, user2])
        session.flush()

        # Создаём расы и армии
        user_race1 = UserRace(user_id=user1.id, race_id=race.id)
        user_race2 = UserRace(user_id=user2.id, race_id=race.id)
        session.add_all([user_race1, user_race2])
        session.flush()

        army1 = Army(user_race_id=user_race1.id, name=f"Army1_{suffix}")
        army2 = Army(user_race_id=user_race2.id, name=f"Army2_{suffix}")
        session.add_all([army1, army2])
        session.flush()

        # Добавляем юнитов
        for race_unit in race_units[:2]:
            session.add(ArmyUnit(army_id=army1.id, race_unit_id=race_unit.id, count=2))
            session.add(ArmyUnit(army_id=army2.id, race_unit_id=race_unit.id, count=2))
        session.commit()

        yield {
            'user1': user1,
            'user2': user2,
            'user1_name': user1_name,
            'user2_name': user2_name,
            'password': password,
            'army1': army1,
            'army2': army2
        }

        # Cleanup
        try:
            session.query(BattleUnit).filter(
                BattleUnit.game_id.in_(
                    session.query(Game.id).filter(
                        (Game.player1_id == user1.id) | (Game.player2_id == user1.id)
                    )
                )
            ).delete(synchronize_session=False)
            session.query(Game).filter(
                (Game.player1_id == user1.id) | (Game.player2_id == user1.id)
            ).delete(synchronize_session=False)
            session.query(ArmyUnit).filter(ArmyUnit.army_id.in_([army1.id, army2.id])).delete(synchronize_session=False)
            session.query(Army).filter(Army.id.in_([army1.id, army2.id])).delete(synchronize_session=False)
            session.query(UserRace).filter(UserRace.id.in_([user_race1.id, user_race2.id])).delete(synchronize_session=False)
            session.query(GameUser).filter(GameUser.id.in_([user1.id, user2.id])).delete(synchronize_session=False)
            session.commit()
        except Exception as e:
            session.rollback()

    def _login(self, username: str, password: str) -> dict:
        """Логин через API."""
        response = requests.post(
            f"{API_BASE_URL}/arena/api/public/login",
            json={"username": username, "password": password},
            verify=False
        )
        return response.json()

    def _get_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def test_multiple_random_moves(self, test_game_in_progress):
        """Тест выполнения нескольких случайных ходов подряд."""
        data = test_game_in_progress

        # Логин
        login1 = self._login(data['user1_name'], data['password'])
        token1 = login1['token']
        player1_id = login1['player']['id']

        login2 = self._login(data['user2_name'], data['password'])
        token2 = login2['token']
        player2_id = login2['player']['id']

        # Создаём игру
        create_response = requests.post(
            f"{API_BASE_URL}/arena/api/public/games/create",
            json={
                "player2_name": data['user2_name'],
                "field_size": "5x5",
                "army_id": data['army1'].id
            },
            headers=self._get_headers(token1),
            verify=False
        )
        game_id = create_response.json()['game_id']

        # Принимаем игру
        requests.post(
            f"{API_BASE_URL}/arena/api/public/games/{game_id}/accept",
            json={"army_id": data['army2'].id},
            headers=self._get_headers(token2),
            verify=False
        )

        # Выполняем несколько ходов
        moves_made = 0
        max_moves = 5

        for _ in range(max_moves * 2):  # Запас на случай неудачных ходов
            if moves_made >= max_moves:
                break

            # Получаем состояние
            state_response = requests.get(
                f"{API_BASE_URL}/arena/api/public/games/{game_id}/state",
                headers=self._get_headers(token1),
                verify=False
            )
            game_state = state_response.json()

            if game_state.get('is_game_over'):
                break

            current_player_id = game_state.get('current_player_id')
            current_token = token1 if current_player_id == player1_id else token2

            # Находим юнита текущего игрока без has_moved
            units = game_state.get('units', [])
            available_units = [
                u for u in units
                if u['player_id'] == current_player_id and u.get('has_moved', 0) == 0
            ]

            if not available_units:
                # Все юниты походили - пропускаем
                continue

            test_unit = random.choice(available_units)

            # Получаем доступные действия
            actions_response = requests.get(
                f"{API_BASE_URL}/arena/api/public/games/{game_id}/units/{test_unit['id']}/actions",
                headers=self._get_headers(current_token),
                verify=False
            )
            actions = actions_response.json()
            moves = actions.get('moves', [])

            if moves:
                target = random.choice(moves)
                move_response = requests.post(
                    f"{API_BASE_URL}/arena/api/public/games/{game_id}/move",
                    json={
                        "unit_id": test_unit['id'],
                        "action": "move",
                        "target_x": target['x'],
                        "target_y": target['y']
                    },
                    headers=self._get_headers(current_token),
                    verify=False
                )

                if move_response.status_code == 200:
                    result = move_response.json()
                    if result.get('success'):
                        moves_made += 1
            else:
                # Нет доступных клеток - пропускаем юнита
                skip_response = requests.post(
                    f"{API_BASE_URL}/arena/api/public/games/{game_id}/move",
                    json={
                        "unit_id": test_unit['id'],
                        "action": "skip"
                    },
                    headers=self._get_headers(current_token),
                    verify=False
                )

        assert moves_made > 0, "Не удалось выполнить ни одного хода"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
