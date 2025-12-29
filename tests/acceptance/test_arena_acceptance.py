#!/usr/bin/env python3
"""
Приёмочные тесты для Godot Arena API.

Тесты работают с production контейнерами и проверяют:
1. Создание тестовых клиентов с армиями
2. Вызов на бой и отказ от боя
3. Принятие боя и его прохождение
4. Управление армией (создание, найм, увольнение юнитов)

Запуск:
    pytest tests/acceptance/test_arena_acceptance.py -v
"""

import os
import random
import pytest
import requests
import hashlib
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import (
    Base, GameRace, RaceUnit, RaceUnitSkin, UnitLevel,
    GameUser, UserRace, UserRaceUnit, Army, ArmyUnit,
    Game, BattleUnit, GameStatus, Field
)


# Production database URL (порт 5434)
PROD_DATABASE_URL = os.getenv('PROD_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')

# API Base URL
API_BASE_URL = os.getenv('API_BASE_URL', 'https://localhost')
ARENA_API_URL = f"{API_BASE_URL}/arena/api/public"

# Disable SSL warnings for localhost
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ArenaAPIClient:
    """HTTP клиент для Godot Arena API."""

    def __init__(self, base_url: str = ARENA_API_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.verify = False
        self.token = None
        self.player_id = None

    def login(self, username: str, password: str) -> dict:
        """Авторизация пользователя."""
        response = self.session.post(
            f"{self.base_url}/login",
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("token")
            self.player_id = data.get("player_id")
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        return response

    def get_me(self) -> dict:
        """Получить информацию о текущем игроке."""
        return self.session.get(f"{self.base_url}/me", timeout=10)

    def get_armies(self) -> dict:
        """Получить список армий игрока."""
        return self.session.get(f"{self.base_url}/armies", timeout=10)

    def create_army(self, name: str, user_race_id: int) -> dict:
        """Создать новую армию."""
        return self.session.post(
            f"{self.base_url}/armies/create",
            json={"name": name, "user_race_id": user_race_id},
            timeout=10
        )

    def delete_army(self, army_id: int) -> dict:
        """Удалить армию."""
        return self.session.post(
            f"{self.base_url}/armies/{army_id}/delete",
            timeout=10
        )

    def get_available_units(self, army_id: int) -> dict:
        """Получить доступных юнитов для найма."""
        return self.session.get(
            f"{self.base_url}/armies/{army_id}/available_units",
            timeout=10
        )

    def hire_unit(self, army_id: int, race_unit_id: int, count: int = 1) -> dict:
        """Нанять юнита в армию."""
        return self.session.post(
            f"{self.base_url}/armies/{army_id}/hire",
            json={"race_unit_id": race_unit_id, "count": count},
            timeout=10
        )

    def dismiss_unit(self, army_id: int, race_unit_id: int, count: int = 1) -> dict:
        """Уволить юнита из армии."""
        return self.session.post(
            f"{self.base_url}/armies/{army_id}/dismiss",
            json={"race_unit_id": race_unit_id, "count": count},
            timeout=10
        )

    def get_pending_games(self) -> dict:
        """Получить ожидающие игры."""
        return self.session.get(f"{self.base_url}/games/pending", timeout=10)

    def create_game(self, opponent_name: str, army_id: int) -> dict:
        """Создать игру (вызвать на бой)."""
        return self.session.post(
            f"{self.base_url}/games/create",
            json={"player2_name": opponent_name, "army_id": army_id},
            timeout=10
        )

    def accept_game(self, game_id: int, army_id: int = None) -> dict:
        """Принять игру."""
        data = {}
        if army_id:
            data["army_id"] = army_id
        return self.session.post(
            f"{self.base_url}/games/{game_id}/accept",
            json=data,
            timeout=10
        )

    def decline_game(self, game_id: int) -> dict:
        """Отклонить игру."""
        return self.session.post(
            f"{self.base_url}/games/{game_id}/decline",
            json={},
            timeout=10
        )

    def get_game_state(self, game_id: int) -> dict:
        """Получить состояние игры."""
        return self.session.get(
            f"{self.base_url}/games/{game_id}/state",
            timeout=10
        )

    def get_unit_actions(self, game_id: int, unit_id: int) -> dict:
        """Получить доступные действия юнита."""
        return self.session.get(
            f"{self.base_url}/games/{game_id}/units/{unit_id}/actions",
            timeout=10
        )

    def move_unit(self, game_id: int, unit_id: int, target_x: int, target_y: int,
                  action: str = "move", target_id: int = None) -> dict:
        """Выполнить ход юнитом."""
        data = {
            "unit_id": unit_id,
            "action": action,
            "target_x": target_x,
            "target_y": target_y
        }
        if target_id:
            data["target_id"] = target_id
        return self.session.post(
            f"{self.base_url}/games/{game_id}/move",
            json=data,
            timeout=10
        )

    def surrender(self, game_id: int) -> dict:
        """Сдаться в игре."""
        return self.session.post(
            f"{self.base_url}/games/{game_id}/surrender",
            json={},
            timeout=10
        )


@pytest.fixture(scope="module")
def db_session():
    """Сессия к production базе данных."""
    engine = create_engine(PROD_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def test_users(db_session):
    """
    Создаёт двух тестовых пользователей с армиями (по одному лучнику).
    """
    session = db_session

    # Генерируем уникальные имена
    suffix = random.randint(100000, 999999)
    user1_name = f"acceptance_test1_{suffix}"
    user2_name = f"acceptance_test2_{suffix}"
    password = "testpass123"
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    # Получаем расу "Люди"
    race = session.query(GameRace).filter_by(name="Люди").first()
    if not race:
        pytest.skip("Раса 'Люди' не найдена в базе данных")

    # Получаем лучника (второй юнит расы обычно лучник)
    archer = session.query(RaceUnit).filter_by(race_id=race.id, name="Лучник").first()
    if not archer:
        # Если нет лучника, берём любого юнита
        archer = session.query(RaceUnit).filter_by(race_id=race.id).first()
    if not archer:
        pytest.skip("Юниты расы не найдены")

    # Создаём пользователей
    user1 = GameUser(
        telegram_id=random.randint(100000000, 999999999),
        username=user1_name,
        balance=Decimal("50000.00"),
        glory=1000,
        password_hash=password_hash
    )
    user2 = GameUser(
        telegram_id=random.randint(100000000, 999999999),
        username=user2_name,
        balance=Decimal("50000.00"),
        glory=1000,
        password_hash=password_hash
    )
    session.add(user1)
    session.add(user2)
    session.flush()

    # Создаём UserRace для обоих
    user_race1 = UserRace(user_id=user1.id, race_id=race.id)
    user_race2 = UserRace(user_id=user2.id, race_id=race.id)
    session.add(user_race1)
    session.add(user_race2)
    session.flush()

    # Создаём армии с одним лучником
    army1 = Army(user_race_id=user_race1.id, name=f"Test Army 1 {suffix}")
    army2 = Army(user_race_id=user_race2.id, name=f"Test Army 2 {suffix}")
    session.add(army1)
    session.add(army2)
    session.flush()

    # Добавляем по одному лучнику в каждую армию
    army_unit1 = ArmyUnit(army_id=army1.id, race_unit_id=archer.id, count=1)
    army_unit2 = ArmyUnit(army_id=army2.id, race_unit_id=archer.id, count=1)
    session.add(army_unit1)
    session.add(army_unit2)
    session.commit()

    data = {
        'user1': user1,
        'user2': user2,
        'user1_name': user1_name,
        'user2_name': user2_name,
        'password': password,
        'army1': army1,
        'army2': army2,
        'user_race1': user_race1,
        'user_race2': user_race2,
        'race': race,
        'archer': archer,
        'suffix': suffix
    }

    yield data

    # Cleanup
    try:
        # Удаляем созданные игры
        session.query(Game).filter(
            (Game.player1_id == user1.id) | (Game.player2_id == user1.id) |
            (Game.player1_id == user2.id) | (Game.player2_id == user2.id)
        ).delete(synchronize_session=False)

        # Удаляем армии (cascade удалит army_units)
        session.query(Army).filter(Army.id.in_([army1.id, army2.id])).delete(synchronize_session=False)

        # Удаляем user_races
        session.query(UserRace).filter(UserRace.id.in_([user_race1.id, user_race2.id])).delete(synchronize_session=False)

        # Удаляем пользователей
        session.query(GameUser).filter(GameUser.id.in_([user1.id, user2.id])).delete(synchronize_session=False)

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Cleanup error: {e}")


@pytest.fixture
def client1(test_users):
    """API клиент для первого пользователя."""
    client = ArenaAPIClient()
    response = client.login(test_users['user1_name'], test_users['password'])
    assert response.status_code == 200, f"Login failed: {response.text}"
    return client


@pytest.fixture
def client2(test_users):
    """API клиент для второго пользователя."""
    client = ArenaAPIClient()
    response = client.login(test_users['user2_name'], test_users['password'])
    assert response.status_code == 200, f"Login failed: {response.text}"
    return client


class TestBattleDecline:
    """Тесты отказа от боя."""

    def test_decline_challenge(self, client1, client2, test_users):
        """Тест: создание вызова и отказ от него."""
        # Клиент 1 вызывает клиента 2 на бой
        create_response = client1.create_game(
            opponent_name=test_users['user2_name'],
            army_id=test_users['army1'].id
        )
        assert create_response.status_code == 200, f"Create game failed: {create_response.text}"
        game_data = create_response.json()
        game_id = game_data.get('game_id')
        assert game_id, "No game_id in response"

        # Клиент 2 видит вызов
        pending_response = client2.get_pending_games()
        assert pending_response.status_code == 200
        pending_data = pending_response.json()
        pending_games = pending_data.get('pending_games', [])
        assert any(g.get('game_id') == game_id for g in pending_games), \
            f"Game {game_id} not in pending games: {pending_games}"

        # Клиент 2 отклоняет вызов
        decline_response = client2.decline_game(game_id)
        assert decline_response.status_code == 200, f"Decline failed: {decline_response.text}"
        decline_data = decline_response.json()
        assert decline_data.get('status') == 'cancelled', f"Unexpected status: {decline_data}"

        # Проверяем что игра больше не в ожидающих
        pending_response = client2.get_pending_games()
        assert pending_response.status_code == 200
        pending_data = pending_response.json()
        pending_games = pending_data.get('pending_games', [])
        assert not any(g.get('game_id') == game_id for g in pending_games), \
            "Game should not be in pending after decline"

    def test_cancel_own_challenge(self, client1, client2, test_users):
        """Тест: отмена собственного вызова."""
        # Клиент 1 вызывает клиента 2 на бой
        create_response = client1.create_game(
            opponent_name=test_users['user2_name'],
            army_id=test_users['army1'].id
        )
        assert create_response.status_code == 200
        game_id = create_response.json().get('game_id')

        # Клиент 1 сам отменяет вызов
        decline_response = client1.decline_game(game_id)
        assert decline_response.status_code == 200, f"Cancel failed: {decline_response.text}"
        assert decline_response.json().get('status') == 'cancelled'


class TestBattleAcceptAndPlay:
    """Тесты принятия боя и его прохождения."""

    def test_accept_and_play_battle(self, client1, client2, test_users, db_session):
        """Тест: принятие боя и игра до завершения (сдача)."""
        # Клиент 1 вызывает клиента 2
        create_response = client1.create_game(
            opponent_name=test_users['user2_name'],
            army_id=test_users['army1'].id
        )
        assert create_response.status_code == 200, f"Create game failed: {create_response.text}"
        game_id = create_response.json().get('game_id')

        # Клиент 2 принимает вызов
        accept_response = client2.accept_game(game_id, army_id=test_users['army2'].id)
        assert accept_response.status_code == 200, f"Accept failed: {accept_response.text}"
        accept_data = accept_response.json()
        assert accept_data.get('status') == 'in_progress', f"Game not started: {accept_data}"

        # Проверяем состояние игры
        state_response = client1.get_game_state(game_id)
        assert state_response.status_code == 200, f"Get state failed: {state_response.text}"
        game_state = state_response.json()

        assert game_state.get('status') == 'in_progress'
        assert 'field' in game_state
        assert 'units' in game_state
        assert len(game_state['units']) >= 2, "Should have at least 2 units"

        # Определяем чей ход
        current_player_id = game_state.get('current_player_id')

        # Завершаем игру сдачей (того кто ходит)
        if current_player_id == test_users['user1'].id:
            surrender_response = client1.surrender(game_id)
        else:
            surrender_response = client2.surrender(game_id)

        assert surrender_response.status_code == 200, f"Surrender failed: {surrender_response.text}"
        surrender_data = surrender_response.json()
        # Surrender возвращает success=True вместо status=completed
        assert surrender_data.get('success') == True, f"Surrender not successful: {surrender_data}"
        assert 'winner_id' in surrender_data, "No winner_id in response"

    def test_play_battle_with_moves(self, client1, client2, test_users, db_session):
        """Тест: принятие боя и выполнение ходов."""
        # Создаём и принимаем игру
        create_response = client1.create_game(
            opponent_name=test_users['user2_name'],
            army_id=test_users['army1'].id
        )
        assert create_response.status_code == 200
        game_id = create_response.json().get('game_id')

        accept_response = client2.accept_game(game_id, army_id=test_users['army2'].id)
        assert accept_response.status_code == 200

        # Получаем состояние игры
        state_response = client1.get_game_state(game_id)
        assert state_response.status_code == 200
        game_state = state_response.json()

        current_player_id = game_state.get('current_player_id')
        current_client = client1 if current_player_id == test_users['user1'].id else client2

        # Находим юнита текущего игрока
        units = game_state.get('units', [])
        my_unit = None
        for unit in units:
            if unit.get('player_id') == current_player_id:
                my_unit = unit
                break

        assert my_unit, "No unit found for current player"

        # Получаем доступные действия
        actions_response = current_client.get_unit_actions(game_id, my_unit['id'])
        assert actions_response.status_code == 200, f"Get actions failed: {actions_response.text}"
        actions = actions_response.json()

        # Делаем ход если есть доступные клетки
        move_cells = actions.get('move_cells', [])
        if move_cells:
            target = move_cells[0]
            move_response = current_client.move_unit(
                game_id=game_id,
                unit_id=my_unit['id'],
                target_x=target['x'],
                target_y=target['y'],
                action='move'
            )
            assert move_response.status_code == 200, f"Move failed: {move_response.text}"

        # Завершаем сдачей
        surrender_response = current_client.surrender(game_id)
        assert surrender_response.status_code == 200


class TestArmyManagement:
    """Тесты управления армией."""

    def test_create_and_delete_army(self, client1, test_users):
        """Тест: создание и удаление армии."""
        # Создаём новую армию
        army_name = f"New Test Army {random.randint(1000, 9999)}"
        create_response = client1.create_army(army_name, test_users['user_race1'].id)
        assert create_response.status_code == 200, f"Create army failed: {create_response.text}"
        army_data = create_response.json()
        new_army_id = army_data.get('army', {}).get('id') or army_data.get('army_id')
        assert new_army_id, f"No army_id in response: {army_data}"

        # Проверяем что армия появилась в списке
        armies_response = client1.get_armies()
        assert armies_response.status_code == 200
        armies = armies_response.json().get('armies', [])
        # API возвращает army_id, не id
        assert any(a.get('army_id') == new_army_id for a in armies), \
            f"New army {new_army_id} not in armies list: {armies}"

        # Удаляем армию
        delete_response = client1.delete_army(new_army_id)
        assert delete_response.status_code == 200, f"Delete army failed: {delete_response.text}"

        # Проверяем что армии больше нет
        armies_response = client1.get_armies()
        assert armies_response.status_code == 200
        armies = armies_response.json().get('armies', [])
        assert not any(a.get('army_id') == new_army_id for a in armies), \
            "Army should be deleted"

    def test_hire_and_dismiss_units(self, client1, test_users, db_session):
        """Тест: найм и увольнение юнитов."""
        army_id = test_users['army1'].id

        # Получаем доступных юнитов для найма
        available_response = client1.get_available_units(army_id)
        assert available_response.status_code == 200, f"Get available units failed: {available_response.text}"
        available_data = available_response.json()
        available_units = available_data.get('units', [])

        if not available_units:
            pytest.skip("No available units for hire")

        # Находим юнита которого можно нанять
        unit_to_hire = None
        for unit in available_units:
            if unit.get('available_count', 0) > 0:
                unit_to_hire = unit
                break

        if not unit_to_hire:
            pytest.skip("No units available for hire")

        race_unit_id = unit_to_hire.get('race_unit_id')
        initial_count = unit_to_hire.get('count_in_army', 0)

        # Нанимаем юнита
        hire_response = client1.hire_unit(army_id, race_unit_id, count=1)
        assert hire_response.status_code == 200, f"Hire failed: {hire_response.text}"

        # Проверяем что количество увеличилось
        available_response = client1.get_available_units(army_id)
        available_data = available_response.json()
        for unit in available_data.get('units', []):
            if unit.get('race_unit_id') == race_unit_id:
                assert unit.get('count_in_army', 0) == initial_count + 1, \
                    f"Unit count should increase after hire"
                break

        # Увольняем юнита
        dismiss_response = client1.dismiss_unit(army_id, race_unit_id, count=1)
        assert dismiss_response.status_code == 200, f"Dismiss failed: {dismiss_response.text}"

        # Проверяем что количество уменьшилось
        available_response = client1.get_available_units(army_id)
        available_data = available_response.json()
        for unit in available_data.get('units', []):
            if unit.get('race_unit_id') == race_unit_id:
                assert unit.get('count_in_army', 0) == initial_count, \
                    f"Unit count should return to initial after dismiss"
                break


class TestFullBattleFlow:
    """Полный сценарий боя от начала до конца."""

    def test_complete_battle_scenario(self, client1, client2, test_users, db_session):
        """
        Полный сценарий:
        1. Создание вызова
        2. Принятие боя
        3. Выполнение нескольких ходов
        4. Атака противника
        5. Завершение боя (победа или сдача)
        """
        # 1. Создаём вызов
        create_response = client1.create_game(
            opponent_name=test_users['user2_name'],
            army_id=test_users['army1'].id
        )
        assert create_response.status_code == 200
        game_id = create_response.json().get('game_id')
        print(f"Game created: {game_id}")

        # 2. Принимаем бой
        accept_response = client2.accept_game(game_id, army_id=test_users['army2'].id)
        assert accept_response.status_code == 200
        print("Game accepted")

        # 3. Выполняем ходы до завершения или максимум 20 ходов
        max_turns = 20
        for turn in range(max_turns):
            # Получаем состояние игры
            state_response = client1.get_game_state(game_id)
            if state_response.status_code != 200:
                break
            game_state = state_response.json()

            # Проверяем не завершена ли игра
            if game_state.get('status') == 'completed':
                print(f"Game completed after {turn} turns")
                print(f"Winner: {game_state.get('winner_id')}")
                return  # Успешное завершение

            current_player_id = game_state.get('current_player_id')
            current_client = client1 if current_player_id == test_users['user1'].id else client2
            other_client = client2 if current_player_id == test_users['user1'].id else client1

            # Находим юнита текущего игрока
            units = game_state.get('units', [])
            my_unit = None
            enemy_unit = None
            for unit in units:
                if unit.get('player_id') == current_player_id and unit.get('count', 0) > 0:
                    my_unit = unit
                elif unit.get('player_id') != current_player_id and unit.get('count', 0) > 0:
                    enemy_unit = unit

            if not my_unit:
                print(f"No unit for player {current_player_id}, surrendering")
                current_client.surrender(game_id)
                break

            # Получаем доступные действия
            actions_response = current_client.get_unit_actions(game_id, my_unit['id'])
            if actions_response.status_code != 200:
                print(f"Failed to get actions: {actions_response.text}")
                break
            actions = actions_response.json()

            # Пытаемся атаковать если есть цели
            attack_targets = actions.get('attack_targets', [])
            if attack_targets and enemy_unit:
                target = attack_targets[0]
                move_response = current_client.move_unit(
                    game_id=game_id,
                    unit_id=my_unit['id'],
                    target_x=target['x'],
                    target_y=target['y'],
                    action='attack',
                    target_id=target.get('unit_id')
                )
                print(f"Turn {turn}: Attack at ({target['x']}, {target['y']})")
            else:
                # Двигаемся к противнику
                move_cells = actions.get('move_cells', [])
                if move_cells:
                    # Выбираем клетку ближе к противнику
                    if enemy_unit:
                        enemy_x = enemy_unit.get('x', 0)
                        enemy_y = enemy_unit.get('y', 0)
                        best_cell = min(move_cells,
                                      key=lambda c: abs(c['x'] - enemy_x) + abs(c['y'] - enemy_y))
                    else:
                        best_cell = move_cells[0]

                    move_response = current_client.move_unit(
                        game_id=game_id,
                        unit_id=my_unit['id'],
                        target_x=best_cell['x'],
                        target_y=best_cell['y'],
                        action='move'
                    )
                    print(f"Turn {turn}: Move to ({best_cell['x']}, {best_cell['y']})")
                else:
                    # Нет доступных ходов - пропускаем
                    print(f"Turn {turn}: No moves available")
                    # Пропуск хода - просто ждём

        # Если дошли до сюда - завершаем сдачей
        state_response = client1.get_game_state(game_id)
        game_state = state_response.json()
        if game_state.get('status') != 'completed':
            current_player_id = game_state.get('current_player_id')
            current_client = client1 if current_player_id == test_users['user1'].id else client2
            surrender_response = current_client.surrender(game_id)
            assert surrender_response.status_code == 200

        # Финальная проверка
        state_response = client1.get_game_state(game_id)
        game_state = state_response.json()
        assert game_state.get('status') == 'completed', \
            f"Game should be completed: {game_state}"


def run_acceptance_tests():
    """Запуск приёмочных тестов."""
    exit_code = pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '-x'  # Остановиться при первой ошибке
    ])
    return exit_code == 0


if __name__ == '__main__':
    import sys
    success = run_acceptance_tests()
    sys.exit(0 if success else 1)
