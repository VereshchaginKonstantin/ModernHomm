#!/usr/bin/env python3
"""
Игровой движок для обработки игровой логики
"""

import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Tuple, Optional, Dict, Set
from sqlalchemy.orm import Session
from db.models import Game, GameStatus, BattleUnit, GameUser, Field, Obstacle, GameLog, Army, ArmyUnit, RaceUnit, UserRace, UserRaceUnit

logger = logging.getLogger(__name__)


def format_coins(amount):
    """Форматирование монет с правильным склонением"""
    # Получаем последнюю цифру и две последние цифры
    amount_int = int(amount) if isinstance(amount, (int, float, Decimal)) else int(float(amount))
    last_digit = amount_int % 10
    last_two_digits = amount_int % 100

    # Определяем правильное склонение
    if last_two_digits >= 11 and last_two_digits <= 19:
        word = "монет"
    elif last_digit == 1:
        word = "монета"
    elif last_digit >= 2 and last_digit <= 4:
        word = "монеты"
    else:
        word = "монет"

    return f"{amount} {word}"


def coords_to_chess(x: int, y: int) -> str:
    """
    Преобразование координат (x, y) в шахматную нотацию (A1, B3, etc.)

    Args:
        x: Координата по горизонтали (столбец)
        y: Координата по вертикали (строка)

    Returns:
        str: Шахматная нотация, например "A1", "B3"
    """
    column = chr(ord('A') + x)  # 0->A, 1->B, 2->C, ...
    row = str(y + 1)  # 0->1, 1->2, 2->3, ...
    return f"{column}{row}"


def chess_to_coords(chess_notation: str) -> Tuple[int, int]:
    """
    Преобразование шахматной нотации (A1, B3, etc.) в координаты (x, y)

    Args:
        chess_notation: Шахматная нотация, например "A1", "B3"

    Returns:
        Tuple[int, int]: Координаты (x, y)
    """
    chess_notation = chess_notation.upper().strip()
    column = ord(chess_notation[0]) - ord('A')  # A->0, B->1, C->2, ...
    row = int(chess_notation[1:]) - 1  # 1->0, 2->1, 3->2, ...
    return (column, row)


class GameEngine:
    """Класс для обработки игровой логики"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def _log_event(self, game_id: int, event_type: str, message: str):
        """
        Записать событие в лог игры

        Args:
            game_id: ID игры
            event_type: Тип события
            message: Текст события
        """
        import json

        # Добавляем время в начало сообщения
        timestamp = datetime.utcnow().strftime("[%H:%M:%S]")
        timestamped_message = f"{timestamp} {message}"

        # Собираем снимок состояния игры
        game_state = self._capture_game_state(game_id)
        game_state_json = json.dumps(game_state, ensure_ascii=False) if game_state else None

        log_entry = GameLog(
            game_id=game_id,
            event_type=event_type,
            message=timestamped_message,
            game_state=game_state_json
        )
        self.db.add(log_entry)
        self.db.flush()

    def _capture_game_state(self, game_id: int) -> dict:
        """
        Захватить текущее состояние игры для сохранения в логе

        Args:
            game_id: ID игры

        Returns:
            dict: Снимок состояния игры
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return None

        units = self.db.query(BattleUnit).filter_by(game_id=game_id).all()

        units_state = []
        for unit in units:
            # Получаем информацию о юните из армии
            unit_name = 'Unknown'
            unit_icon = '?'
            if unit.army_unit and unit.army_unit.race_unit:
                unit_name = unit.army_unit.race_unit.name
                # Используем иконку уровня юнита
                if unit.army_unit.race_unit.unit_level:
                    unit_icon = unit.army_unit.race_unit.unit_level.icon
            unit_info = {
                'id': unit.id,
                'player_id': unit.player_id,
                'position_x': unit.position_x,
                'position_y': unit.position_y,
                'total_count': unit.total_count,
                'has_moved': unit.has_moved,
                'unit_name': unit_name,
                'unit_icon': unit_icon
            }
            units_state.append(unit_info)

        return {
            'current_player_id': game.current_player_id,
            'status': game.status.value if game.status else None,
            'units': units_state
        }

    def create_game(self, player1_id: int, player2_username: str, player1_army_id: int, field_name: str = "7x7") -> Tuple[Optional[Game], str]:
        """
        Создание новой игры с выбранной армией

        Args:
            player1_id: ID игрока, создающего игру
            player2_username: Имя второго игрока
            player1_army_id: ID армии игрока 1
            field_name: Название поля (по умолчанию "7x7")

        Returns:
            Tuple[Game, str]: Созданная игра и сообщение
        """
        # Найти игроков
        player1 = self.db.query(GameUser).filter_by(id=player1_id).first()
        if not player1:
            return None, "Игрок 1 не найден"

        # Ищем по username
        player2 = self.db.query(GameUser).filter_by(username=player2_username).first()
        if not player2:
            return None, f"Игрок с никнеймом '{player2_username}' не найден"

        if player1.id == player2.id:
            return None, "Нельзя играть с самим собой"

        # Проверить армию игрока 1
        player1_army = self.db.query(Army).filter_by(id=player1_army_id).first()
        if not player1_army:
            return None, "Армия не найдена"

        # Проверить что армия принадлежит игроку
        player1_user_race = player1_army.user_race
        if not player1_user_race or player1_user_race.user_id != player1.id:
            return None, "Эта армия вам не принадлежит"

        # Проверить что в армии есть юниты
        player1_army_units = self.db.query(ArmyUnit).filter(
            ArmyUnit.army_id == player1_army_id,
            ArmyUnit.count > 0
        ).all()
        if not player1_army_units:
            return None, "В вашей армии нет юнитов"

        # Найти или создать поле
        field = self.db.query(Field).filter_by(name=field_name).first()
        if not field:
            # Создать стандартные поля, если их нет
            self._create_default_fields()
            field = self.db.query(Field).filter_by(name=field_name).first()
            if not field:
                return None, f"Поле '{field_name}' не найдено"

        # Создать игру (армия игрока 2 будет установлена при принятии)
        game = Game(
            player1_id=player1.id,
            player2_id=player2.id,
            player1_army_id=player1_army_id,
            player2_army_id=None,  # Будет установлено при принятии игры
            field_id=field.id,
            status=GameStatus.WAITING
        )
        self.db.add(game)
        self.db.flush()

        # Разместить юниты армии игрока 1
        self._place_army_units(game, player1, player1_army_units, 1)

        # Сгенерировать препятствия
        self._generate_obstacles(game)

        # Логировать создание игры
        self._log_event(game.id, "game_created", f"⚔️ Игра создана! {player1.username} вызвал на бой {player2.username}")

        self.db.commit()
        return game, f"Игра создана! Ожидание принятия игроком {player2_username}"

    def accept_game(self, game_id: int, player_id: int, player2_army_id: int) -> Tuple[bool, str]:
        """
        Принятие игры вторым игроком с выбранной армией

        Args:
            game_id: ID игры
            player_id: ID игрока, принимающего игру
            player2_army_id: ID армии игрока 2

        Returns:
            Tuple[bool, str]: Успех и сообщение
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return False, "Игра не найдена"

        if game.status != GameStatus.WAITING:
            return False, "Игра уже начата или завершена"

        if game.player2_id != player_id:
            return False, "Вы не являетесь участником этой игры"

        # Проверить армию игрока 2
        player2_army = self.db.query(Army).filter_by(id=player2_army_id).first()
        if not player2_army:
            return False, "Армия не найдена"

        # Проверить что армия принадлежит игроку
        player2_user_race = player2_army.user_race
        if not player2_user_race or player2_user_race.user_id != player_id:
            return False, "Эта армия вам не принадлежит"

        # Проверить что в армии есть юниты
        player2_army_units = self.db.query(ArmyUnit).filter(
            ArmyUnit.army_id == player2_army_id,
            ArmyUnit.count > 0
        ).all()
        if not player2_army_units:
            return False, "В вашей армии нет юнитов"

        # Разместить юниты армии игрока 2
        player2 = self.db.query(GameUser).filter_by(id=player_id).first()
        self._place_army_units(game, player2, player2_army_units, 2)

        # Установить армию игрока 2
        game.player2_army_id = player2_army_id

        # Начать игру
        game.status = GameStatus.IN_PROGRESS
        game.started_at = datetime.utcnow()
        game.current_player_id = game.player1_id  # Первый игрок ходит первым
        game.last_move_at = datetime.utcnow()

        # Логировать начало игры
        player1 = self.db.query(GameUser).filter_by(id=game.player1_id).first()
        self._log_event(game.id, "game_started", f"🎮 Игра началась! Первый ход: {player1.username}")

        self.db.commit()
        return True, "Игра начата! Ходит первый игрок"

    def move_unit(self, game_id: int, player_id: int, battle_unit_id: int, target_x: int, target_y: int) -> Tuple[bool, str, bool]:
        """
        Перемещение юнита

        Args:
            game_id: ID игры
            player_id: ID игрока
            battle_unit_id: ID юнита в бою
            target_x: Целевая координата X
            target_y: Целевая координата Y

        Returns:
            Tuple[bool, str, bool]: Успех, сообщение, сменился ли ход
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return False, "Игра не найдена", False

        if game.status != GameStatus.IN_PROGRESS:
            return False, "Игра не в процессе", False

        if game.current_player_id != player_id:
            return False, "Сейчас не ваш ход", False

        battle_unit = self.db.query(BattleUnit).filter_by(id=battle_unit_id, game_id=game_id).first()
        if not battle_unit:
            return False, "Юнит не найден", False

        if battle_unit.player_id != player_id:
            return False, "Это не ваш юнит", False

        if battle_unit.has_moved:
            return False, "Этот юнит уже совершил ход", False

        # Проверить, что цель в пределах поля
        if target_x < 0 or target_x >= game.field.width or target_y < 0 or target_y >= game.field.height:
            return False, "Цель за пределами поля", False

        # Проверить, что цель свободна
        occupied = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game_id,
            BattleUnit.position_x == target_x,
            BattleUnit.position_y == target_y
        ).first()
        if occupied:
            return False, "Эта позиция занята", False

        # Проверить, что на цели нет препятствия
        obstacle = self.db.query(Obstacle).filter(
            Obstacle.game_id == game_id,
            Obstacle.position_x == target_x,
            Obstacle.position_y == target_y
        ).first()
        if obstacle:
            return False, "На этой позиции препятствие", False

        # Получить характеристики юнита
        unit = self._get_unit_stats(battle_unit)

        # Проверить дистанцию (манхэттенское расстояние)
        distance = abs(battle_unit.position_x - target_x) + abs(battle_unit.position_y - target_y)
        if distance > unit['speed']:
            return False, f"Слишком далеко! Скорость юнита: {unit['speed']}, расстояние: {distance}", False

        # Переместить юнита
        old_pos = (battle_unit.position_x, battle_unit.position_y)
        battle_unit.position_x = target_x
        battle_unit.position_y = target_y
        battle_unit.has_moved = 1

        # Проверить, все ли юниты текущего игрока походили
        turn_switched = False
        if self._all_units_moved(game, player_id):
            self._switch_turn(game)
            turn_switched = True

        game.last_move_at = datetime.utcnow()

        # Логируем перемещение
        player = self.db.query(GameUser).filter_by(id=player_id).first()
        unit_name = unit['name'] if unit else "Юнит"
        self._log_event(game.id, "move", f"🚶 {player.username}: {unit_name} {old_pos} → ({target_x}, {target_y})")

        self.db.commit()

        return True, f"Юнит перемещен с {old_pos} на ({target_x}, {target_y})", turn_switched

    def get_available_movement_cells(self, game_id: int, battle_unit_id: int) -> List[Tuple[int, int]]:
        """
        Получить список доступных для перемещения клеток для юнита.
        Использует BFS для поиска всех достижимых клеток с учетом:
        - Скорости юнита (максимальное расстояние)
        - Занятых клеток (нельзя проходить через другие юниты)
        - Направлений движения (только вверх, вниз, влево, вправо - без диагоналей)

        Args:
            game_id: ID игры
            battle_unit_id: ID юнита на поле боя

        Returns:
            List[Tuple[int, int]]: Список координат (x, y) доступных клеток
        """
        from collections import deque

        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return []

        battle_unit = self.db.query(BattleUnit).filter_by(id=battle_unit_id, game_id=game_id).first()
        if not battle_unit:
            return []

        # Получить характеристики юнита
        unit = self._get_unit_stats(battle_unit)
        speed = unit['speed']
        start_x, start_y = battle_unit.position_x, battle_unit.position_y

        # Получить размеры поля
        field_width = game.field.width
        field_height = game.field.height

        # Получить все занятые позиции (кроме текущей позиции юнита)
        occupied_positions = set()
        for bu in game.battle_units:
            if bu.id != battle_unit_id:
                alive_count = self._count_alive_units(bu)
                if alive_count > 0:
                    occupied_positions.add((bu.position_x, bu.position_y))

        # Добавить препятствия
        for obstacle in game.obstacles:
            occupied_positions.add((obstacle.position_x, obstacle.position_y))

        # BFS для поиска всех достижимых клеток
        available_cells = []
        visited = {(start_x, start_y): 0}  # позиция -> расстояние от старта
        queue = deque([(start_x, start_y, 0)])  # (x, y, distance)

        # Направления движения: вверх, вниз, влево, вправо (без диагоналей)
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        while queue:
            current_x, current_y, distance = queue.popleft()

            # Проверяем все соседние клетки
            for dx, dy in directions:
                next_x = current_x + dx
                next_y = current_y + dy
                next_distance = distance + 1

                # Проверка границ поля
                if not (0 <= next_x < field_width and 0 <= next_y < field_height):
                    continue

                # Проверка, что не превышена скорость
                if next_distance > speed:
                    continue

                # Проверка, что клетка не занята
                if (next_x, next_y) in occupied_positions:
                    continue

                # Проверка, что клетка еще не посещена или найден более короткий путь
                if (next_x, next_y) not in visited:
                    visited[(next_x, next_y)] = next_distance
                    available_cells.append((next_x, next_y))
                    queue.append((next_x, next_y, next_distance))

        return available_cells

    def get_valid_moves(self, battle_unit_id: int) -> List[Dict]:
        """
        Публичный метод для получения доступных перемещений юнита.
        Возвращает список словарей с координатами {x, y}.

        Args:
            battle_unit_id: ID юнита на поле боя

        Returns:
            List[Dict]: Список доступных клеток [{x, y}, ...]
        """
        battle_unit = self.db.query(BattleUnit).filter_by(id=battle_unit_id).first()
        if not battle_unit:
            return []

        cells = self.get_available_movement_cells(battle_unit.game_id, battle_unit_id)
        return [{'x': x, 'y': y} for x, y in cells]

    def get_valid_attacks(self, battle_unit_id: int) -> List[Dict]:
        """
        Публичный метод для получения доступных целей для атаки юнита.
        Возвращает список словарей с информацией о целях.

        Args:
            battle_unit_id: ID юнита на поле боя

        Returns:
            List[Dict]: Список доступных целей [{id, x, y, name}, ...]
        """
        battle_unit = self.db.query(BattleUnit).filter_by(id=battle_unit_id).first()
        if not battle_unit:
            return []

        game = self.db.query(Game).filter_by(id=battle_unit.game_id).first()
        if not game:
            return []

        targets = self._get_available_targets(game, battle_unit)
        return [{
            'id': t['unit_id'],
            'x': t['position'][0],
            'y': t['position'][1],
            'name': t['unit_name']
        } for t in targets]

    def attack(self, game_id: int, player_id: int, attacker_id: int, target_id: int) -> Tuple[bool, str, bool]:
        """
        Атака юнита

        Args:
            game_id: ID игры
            player_id: ID игрока
            attacker_id: ID атакующего юнита
            target_id: ID цели

        Returns:
            Tuple[bool, str, bool]: Успех, сообщение с подробностями атаки, сменился ли ход
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return False, "Игра не найдена", False

        if game.status != GameStatus.IN_PROGRESS:
            return False, "Игра не в процессе", False

        if game.current_player_id != player_id:
            return False, "Сейчас не ваш ход", False

        attacker = self.db.query(BattleUnit).filter_by(id=attacker_id, game_id=game_id).first()
        if not attacker:
            return False, "Атакующий юнит не найден", False

        if attacker.player_id != player_id:
            return False, "Это не ваш юнит", False

        if attacker.has_moved:
            return False, "Этот юнит уже совершил ход", False

        target = self.db.query(BattleUnit).filter_by(id=target_id, game_id=game_id).first()
        if not target:
            return False, "Цель не найдена", False

        if target.player_id == player_id:
            return False, "Нельзя атаковать своих юнитов", False

        # Проверить дистанцию
        attacker_unit = self._get_unit_stats(attacker)
        distance = abs(attacker.position_x - target.position_x) + abs(attacker.position_y - target.position_y)
        if distance > attacker_unit['range']:
            return False, f"Цель слишком далеко! Дальность атаки: {attacker_unit['range']}, расстояние: {distance}", False

        # Проверить линию видимости
        if not self._has_line_of_sight(attacker.position_x, attacker.position_y, target.position_x, target.position_y, game):
            return False, "Нет линии видимости! Между вами и целью есть препятствие или другой юнит.", False

        # Рассчитать урон
        damage, is_crit, combat_log = self._calculate_damage(attacker, target)

        # Применить урон
        units_killed = self._apply_damage(target, damage)

        # Обработать контратаку - вероятность контратаки всегда 50%
        attacker_unit = self._get_unit_stats(attacker)
        target_unit = self._get_unit_stats(target)
        counterattack_damage = 0

        # Проверяем что цель жива и был нанесен урон
        if target.total_count > 0 and damage > 0:
            # Вероятность контратаки всегда 50%
            counterattack_roll = random.random()
            if counterattack_roll < 0.5:
                # Рассчитать контратаку как урон цели с коэффициентом
                counterattack_coef = float(target_unit['counterattack_chance'])

                # Базовый урон контратаки (среднее между min и max)
                base_counter_damage = (target_unit['min_damage'] + target_unit['max_damage']) // 2
                alive_defenders = self._count_alive_units(target)

                # Проверка, не камикадзе ли защитник
                is_target_kamikaze = bool(target_unit['is_kamikaze'])
                if is_target_kamikaze:
                    alive_defenders = 1

                # Применить коэффициент контратаки и количество юнитов
                counterattack_damage = int(base_counter_damage * counterattack_coef * alive_defenders)

                # Применить контратаку к атакующему
                if counterattack_damage > 0:
                    counter_units_killed = self._apply_damage(attacker, counterattack_damage)

                    combat_log += f"\n\n🔄 КОНТРАТАКА! {target_unit['name']} наносит ответный урон {attacker_unit['name']}!\n"
                    combat_log += f"   Вероятность контратаки: 50.0% (бросок: {counterattack_roll*100:.1f}%)\n"
                    combat_log += f"   Коэффициент урона контратаки: {counterattack_coef*100:.1f}%\n"
                    combat_log += f"   Базовый урон: {base_counter_damage} x {alive_defenders} юнитов x {counterattack_coef:.2f} = {counterattack_damage}\n"
                    combat_log += f"   ⚡ Урон от контратаки: {counterattack_damage}"

                    if counter_units_killed > 0:
                        combat_log += f"\n   ⚰️ Убито атакующих юнитов: {counter_units_killed}"
            else:
                # Контратака не сработала
                combat_log += f"\n\n❌ Контратака не сработала (вероятность 50%, бросок: {counterattack_roll*100:.1f}%)"

        # Обработать камикадзе - уменьшить счетчик юнитов на 1 после атаки
        if attacker_unit['is_kamikaze'] and attacker.total_count > 0:
            attacker.total_count -= 1
            combat_log += f"\n\n💣 КАМИКАДЗЕ: {attacker_unit['name']} потерял 1 юнита после атаки (осталось: {attacker.total_count})"

            # Если камикадзе юниты закончились, обнулить HP
            if attacker.total_count == 0:
                attacker.remaining_hp = 0
                combat_log += f"\n⚰️ Все камикадзе юниты {attacker_unit['name']} погибли!"

        # Обновить кураж (morale) в зависимости от результата атаки
        if units_killed > 0:
            # Атакующий убил юнитов - повышение куража
            attacker.morale = 110  # Коэффициент 1.1 (бонус +10%)
            # Защищающийся потерял юнитов - понижение куража
            if target.total_count > 0:  # Если юнит еще жив
                target.morale = 90  # Коэффициент 0.9 (штраф -10%)

        # Обновить усталость
        if is_crit or damage > 0:
            attacker.fatigue = max(float(attacker.fatigue) - 5, 0)
        else:
            attacker.fatigue = min(float(attacker.fatigue) + 10, 100)

        # Применить эффект отравления (если атакующий имеет способность отравления)
        if target.total_count > 0 and damage > 0:
            poison_msg = self._apply_poison_effect(attacker, target)
            if poison_msg:
                combat_log += poison_msg

        # Удалить мёртвый юнит из базы (если все юниты убиты)
        if target.total_count == 0:
            logger.info(f"Удаление мёртвого юнита: id={target.id}, position=({target.position_x}, {target.position_y})")
            self.db.delete(target)

        # Удалить камикадзе юнит, если все юниты погибли
        if attacker.total_count == 0:
            logger.info(f"Удаление мёртвого камикадзе юнита: id={attacker.id}, position=({attacker.position_x}, {attacker.position_y})")
            self.db.delete(attacker)
        else:
            attacker.has_moved = 1

        game.last_move_at = datetime.utcnow()

        # Добавляем информацию об убитых юнитах защитника в combat_log
        if units_killed > 0:
            combat_log += f"\n\n⚰️ Убито юнитов: {units_killed}"

        # Логировать атаку ПЕРЕД завершением игры, чтобы game_ended был последним
        attacker_player = self.db.query(GameUser).filter_by(id=player_id).first()
        self._log_event(game.id, "attack", f"⚔️ {attacker_player.username}: {combat_log}")

        # Проверить, все ли юниты игрока мертвы
        turn_switched = False
        winner_id = self._check_game_over(game)
        if winner_id:
            # Завершение игры - _complete_game создаст отдельный лог game_ended (будет последним)
            reward, stats = self._complete_game(game, winner_id)
            # Не добавляем результаты игры в combat_log - они будут в отдельном сообщении
        else:
            # Проверить, все ли юниты текущего игрока походили
            if self._all_units_moved(game, player_id):
                self._switch_turn(game)
                turn_switched = True

        self.db.commit()

        # combat_log уже содержит информацию об убитых юнитах (если units_killed > 0)
        # Добавляем "Убито юнитов: X" только если не было убито (чтобы regex на фронте работал)
        if units_killed == 0:
            result_msg = f"Атака выполнена!\n{combat_log}\nУбито юнитов: 0"
        else:
            result_msg = f"Атака выполнена!\n{combat_log}"
        return True, result_msg, turn_switched

    def skip_unit_turn(self, game_id: int, player_id: int, unit_id: int) -> Tuple[bool, str, bool]:
        """
        Пропустить ход юнита

        Args:
            game_id: ID игры
            player_id: ID игрока
            unit_id: ID юнита

        Returns:
            Tuple[bool, str, bool]: Успех, сообщение, сменился ли ход
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return False, "Игра не найдена", False

        if game.status != GameStatus.IN_PROGRESS:
            return False, "Игра не в процессе", False

        if game.current_player_id != player_id:
            return False, "Сейчас не ваш ход", False

        unit = self.db.query(BattleUnit).filter_by(id=unit_id, game_id=game_id).first()
        if not unit:
            return False, "Юнит не найден", False

        if unit.player_id != player_id:
            return False, "Это не ваш юнит", False

        if unit.has_moved:
            return False, "Этот юнит уже совершил ход", False

        # Пометить юнита как сделавшего ход
        unit.has_moved = 1

        # Проверить, все ли юниты походили
        turn_switched = False
        if self._all_units_moved(game, player_id):
            self._switch_turn(game)
            turn_switched = True

        game.last_move_at = datetime.utcnow()
        self.db.commit()

        return True, "Ход пропущен", turn_switched

    def defer_unit(self, game_id: int, player_id: int, unit_id: int) -> Tuple[bool, str]:
        """
        Отложить ход юнита - юнит перемещается в конец очереди

        Args:
            game_id: ID игры
            player_id: ID игрока
            unit_id: ID юнита

        Returns:
            Tuple[bool, str]: Успех, сообщение
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return False, "Игра не найдена"

        if game.status != GameStatus.IN_PROGRESS:
            return False, "Игра не в процессе"

        if game.current_player_id != player_id:
            return False, "Сейчас не ваш ход"

        unit = self.db.query(BattleUnit).filter_by(id=unit_id, game_id=game_id).first()
        if not unit:
            return False, "Юнит не найден"

        if unit.player_id != player_id:
            return False, "Это не ваш юнит"

        if unit.has_moved:
            return False, "Этот юнит уже совершил ход"

        # Проверяем, есть ли другие юниты, которые могут ходить
        other_unmoved = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game_id,
            BattleUnit.player_id == player_id,
            BattleUnit.has_moved == 0,
            BattleUnit.id != unit_id
        ).count()

        if other_unmoved == 0:
            return False, "Нет других юнитов для хода"

        # Увеличиваем приоритет (чем больше, тем позже в очереди)
        # Находим максимальный deferred среди непоходивших юнитов этого игрока
        max_deferred = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game_id,
            BattleUnit.player_id == player_id,
            BattleUnit.has_moved == 0
        ).with_entities(BattleUnit.deferred).order_by(BattleUnit.deferred.desc()).first()

        unit.deferred = (max_deferred[0] if max_deferred else 0) + 1

        game.last_move_at = datetime.utcnow()
        self.db.commit()

        return True, "Юнит отложен в конец очереди"

    def render_field(self, game_id: int) -> str:
        """
        Отрисовка игрового поля

        Args:
            game_id: ID игры

        Returns:
            str: Текстовое представление поля
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return "Игра не найдена"

        field = game.field
        width, height = field.width, field.height

        # Создать пустое поле
        grid = [["[___]" for _ in range(width)] for _ in range(height)]

        # Разместить юниты
        for battle_unit in game.battle_units:
            x, y = battle_unit.position_x, battle_unit.position_y
            unit = self._get_unit_stats(battle_unit)

            # Подсчитать живых юнитов
            alive_count = self._count_alive_units(battle_unit)

            if alive_count > 0:
                # Проверить, есть ли кастомная иконка для этого юнита
                custom_icon = self.db.query(UnitCustomIcon).filter_by(unit_id=unit.id).first()
                icon = custom_icon.custom_icon if custom_icon else unit.icon
                grid[y][x] = f"[{icon}{alive_count}]"

        # Собрать поле в строку
        result = f"Игра #{game.id} - {game.player1.username} vs {game.player2.username}\n"
        result += f"Статус: {game.status.value}\n"

        if game.status == GameStatus.IN_PROGRESS:
            current_player = game.player1.username if game.current_player_id == game.player1_id else game.player2.username
            result += f"Ход игрока: {current_player}\n"

        result += "\n"

        # Добавить заголовок с буквами столбцов (A B C D...)
        column_labels = "   " + "  ".join([chr(ord('A') + x) for x in range(width)]) + "\n"
        result += column_labels

        # Добавить строки с номерами
        for y in range(height):
            row_label = f"{y + 1} "  # Номер строки (1, 2, 3...)
            result += row_label + "".join(grid[y]) + "\n"

        return result

    def get_available_actions(self, game_id: int, player_id: int) -> Dict:
        """
        Получить доступные действия для игрока

        Args:
            game_id: ID игры
            player_id: ID игрока

        Returns:
            Dict: Словарь с доступными действиями
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return {"error": "Игра не найдена"}

        if game.status == GameStatus.WAITING:
            if game.player2_id == player_id:
                return {"action": "accept", "message": "Примите игру командой /accept_game"}
            else:
                return {"action": "wait", "message": "Ожидание принятия игры"}

        if game.status == GameStatus.COMPLETED:
            return {"action": "none", "message": "Игра завершена"}

        if game.current_player_id != player_id:
            return {"action": "wait", "message": "Ожидайте своего хода"}

        # Получить юниты игрока, которые еще не походили (сортировка по deferred)
        available_units = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game_id,
            BattleUnit.player_id == player_id,
            BattleUnit.has_moved == 0
        ).order_by(BattleUnit.deferred.asc()).all()

        actions = []
        for unit in available_units:
            alive_count = self._count_alive_units(unit)
            if alive_count > 0:
                unit_type = self._get_unit_stats(unit)
                actions.append({
                    "unit_id": unit.id,
                    "unit_name": unit_type['name'],
                    "position": (unit.position_x, unit.position_y),
                    "can_move": True,
                    "targets": self._get_available_targets(game, unit)
                })

        return {"action": "play", "units": actions}

    # Вспомогательные методы

    def _get_unit_stats(self, battle_unit: BattleUnit) -> dict:
        """
        Получить характеристики юнита из армии

        Args:
            battle_unit: Юнит в бою

        Returns:
            dict: Характеристики юнита
        """
        army_unit = battle_unit.army_unit
        race_unit = army_unit.race_unit if army_unit else None

        if not race_unit:
            return {
                'name': 'Unknown',
                'icon': '?',
                'attack': 10,
                'defense': 5,
                'min_damage': 1,
                'max_damage': 3,
                'health': 10,
                'speed': 4,
                'initiative': 10,
                'range': 1,
                'luck': 0,
                'crit_chance': 0,
                'dodge_chance': 0,
                'counterattack_chance': 0,
                'is_flying': False,
                'is_kamikaze': False,
                'regeneration_health': 0,
                'poison_damage': 0,
                'poison_turns': 0,
                'poison_immunity': False,
                'price': 0
            }

        # Получить иконку уровня
        icon = race_unit.unit_level.icon if race_unit.unit_level else '?'

        return {
            'name': race_unit.name,
            'icon': icon,
            'attack': race_unit.attack,
            'defense': race_unit.defense,
            'min_damage': race_unit.min_damage,
            'max_damage': race_unit.max_damage,
            'health': race_unit.health,
            'speed': race_unit.speed,
            'initiative': race_unit.initiative,
            'range': race_unit.range,
            'luck': float(race_unit.luck or 0),
            'crit_chance': float(race_unit.crit_chance or 0),
            'dodge_chance': float(race_unit.dodge_chance or 0),
            'counterattack_chance': float(race_unit.counterattack_chance or 0),
            'is_flying': race_unit.is_flying,
            'is_kamikaze': race_unit.is_kamikaze,
            'regeneration_health': race_unit.regeneration_health or 0,
            'poison_damage': race_unit.poison_damage or 0,
            'poison_turns': race_unit.poison_turns or 0,
            'poison_immunity': race_unit.poison_immunity,
            'price': self._calculate_prestige(race_unit)
        }

    def _calculate_prestige(self, race_unit: RaceUnit) -> int:
        """Рассчитать престиж юнита"""
        # Простой расчет престижа на основе характеристик
        base = (
            race_unit.attack +
            race_unit.defense +
            race_unit.health +
            race_unit.min_damage +
            race_unit.max_damage
        )
        range_bonus = race_unit.range * (race_unit.attack + race_unit.defense) if race_unit.range > 1 else 0
        flying_bonus = 2 * (race_unit.attack + race_unit.defense) if race_unit.is_flying else 0
        return int(base + range_bonus + flying_bonus)

    def _create_default_fields(self):
        """Создать стандартные поля"""
        fields = [
            Field(name="5x5", width=5, height=5),
            Field(name="7x7", width=7, height=7),
            Field(name="5x7", width=5, height=7),
            Field(name="10x10", width=10, height=10),
        ]
        for field in fields:
            existing = self.db.query(Field).filter_by(name=field.name).first()
            if not existing:
                self.db.add(field)
        self.db.commit()

    def _place_army_units(self, game: Game, player: GameUser, army_units: List[ArmyUnit], side: int):
        """
        Разместить юниты армии на поле

        Args:
            game: Игра
            player: Игрок
            army_units: Список юнитов армии
            side: Сторона (1 или 2)
        """
        field = game.field

        # Определить стартовые позиции
        if side == 1:
            # Игрок 1 - левая сторона
            positions = [(0, y) for y in range(min(len(army_units), field.height))]
        else:
            # Игрок 2 - правая сторона
            positions = [(field.width - 1, y) for y in range(min(len(army_units), field.height))]

        for i, army_unit in enumerate(army_units[:len(positions)]):
            x, y = positions[i]
            race_unit = army_unit.race_unit

            # Получаем здоровье из RaceUnit (+ бусты если есть UserRaceUnit)
            health = race_unit.health

            battle_unit = BattleUnit(
                game_id=game.id,
                army_unit_id=army_unit.id,
                player_id=player.id,
                position_x=x,
                position_y=y,
                total_count=army_unit.count,
                remaining_hp=health,
                morale=100,  # Изначально 100 = коэффициент 1.0 (нейтральный)
                fatigue=0,
                has_moved=0
            )
            self.db.add(battle_unit)

    def _generate_obstacles(self, game: Game):
        """
        Генерировать случайные препятствия на игровом поле

        Args:
            game: Игра
        """
        field = game.field

        # Количество препятствий зависит от размера поля (примерно 10-15% клеток)
        num_obstacles = random.randint(field.width * field.height // 10, field.width * field.height // 7)

        # Получить занятые позиции (юниты)
        occupied = set()
        for battle_unit in game.battle_units:
            occupied.add((battle_unit.position_x, battle_unit.position_y))

        # Сгенерировать препятствия
        obstacles_generated = 0
        attempts = 0
        max_attempts = num_obstacles * 3  # Максимум попыток

        while obstacles_generated < num_obstacles and attempts < max_attempts:
            x = random.randint(0, field.width - 1)
            y = random.randint(0, field.height - 1)

            # Проверить, что позиция не занята
            if (x, y) not in occupied:
                obstacle = Obstacle(
                    game_id=game.id,
                    position_x=x,
                    position_y=y
                )
                self.db.add(obstacle)
                occupied.add((x, y))
                obstacles_generated += 1

            attempts += 1

    def _has_line_of_sight(self, start_x: int, start_y: int, end_x: int, end_y: int, game: Game) -> bool:
        """
        Проверить, есть ли линия видимости между двумя точками

        Использует алгоритм Bresenham для проверки препятствий на линии между точками.
        Диагональные атаки разрешены, если на пути нет препятствий или других юнитов.

        Args:
            start_x: Начальная координата X
            start_y: Начальная координата Y
            end_x: Конечная координата X
            end_y: Конечная координата Y
            game: Игра

        Returns:
            bool: True если линия видимости есть, False иначе
        """
        # Получить все занятые позиции (юниты и препятствия)
        occupied = set()

        # Добавить позиции юнитов
        for battle_unit in game.battle_units:
            alive_count = self._count_alive_units(battle_unit)
            if alive_count > 0:
                occupied.add((battle_unit.position_x, battle_unit.position_y))

        # Добавить позиции препятствий
        for obstacle in game.obstacles:
            occupied.add((obstacle.position_x, obstacle.position_y))

        # Убрать начальную и конечную точки из проверки
        if (start_x, start_y) in occupied:
            occupied.remove((start_x, start_y))
        if (end_x, end_y) in occupied:
            occupied.remove((end_x, end_y))

        # Алгоритм Bresenham для проверки линии
        dx = abs(end_x - start_x)
        dy = abs(end_y - start_y)

        x = start_x
        y = start_y

        x_inc = 1 if end_x > start_x else -1
        y_inc = 1 if end_y > start_y else -1

        # Если линия горизонтальная или вертикальная
        if dx == 0:  # Вертикальная линия
            for i in range(1, dy):
                y += y_inc
                if (x, y) in occupied:
                    return False
            return True

        if dy == 0:  # Горизонтальная линия
            for i in range(1, dx):
                x += x_inc
                if (x, y) in occupied:
                    return False
            return True

        # Для диагональных линий используем Bresenham
        if dx > dy:
            error = dx / 2
            while x != end_x:
                x += x_inc
                error -= dy
                if error < 0:
                    y += y_inc
                    error += dx

                # Не проверяем конечную точку
                if x != end_x and (x, y) in occupied:
                    return False
        else:
            error = dy / 2
            while y != end_y:
                y += y_inc
                error -= dx
                if error < 0:
                    x += x_inc
                    error += dy

                # Не проверяем конечную точку
                if y != end_y and (x, y) in occupied:
                    return False

        return True

    def _calculate_damage(self, attacker: BattleUnit, target: BattleUnit) -> Tuple[int, bool, str]:
        """
        Рассчитать урон с учетом случайности и всех модификаторов

        Args:
            attacker: Атакующий юнит
            target: Цель

        Returns:
            Tuple[int, bool, str]: Урон, критический удар, лог боя
        """
        attacker_unit = self._get_unit_stats(attacker)
        target_unit = self._get_unit_stats(target)

        # Подсчет количества атакующих юнитов
        alive_attackers = self._count_alive_units(attacker)

        # Проверка камикадзе (в расчете урона учитывается только 1 юнит)
        is_kamikaze = bool(attacker_unit['is_kamikaze'])
        actual_attackers = alive_attackers  # Сохраняем реальное количество для лога
        if is_kamikaze:
            alive_attackers = 1  # Камикадзе наносит урон только за 1 юнита

        # Проверка уклонения (dodge)
        dodge_chance = float(target_unit['dodge_chance'])
        dodge_roll = random.random()
        is_dodged = dodge_roll < dodge_chance

        if is_dodged:
            # Уклонение успешно - урон 0
            attacker_display = f"x{actual_attackers}" if not is_kamikaze else f"x{actual_attackers} 💣КАМИКАДЗЕ💣"
            log = f"⚔️ {attacker_unit['name']} ({attacker_display}) атакует {target_unit['name']}\n\n"
            log += f"🌀 УКЛОНЕНИЕ! {target_unit['name']} уклонился от атаки!\n"
            log += f"   Шанс уклонения: {dodge_chance*100:.1f}% (бросок: {dodge_roll*100:.1f}%)\n"
            log += f"   ⚡ ИТОГОВЫЙ УРОН: 0"
            return 0, False, log

        # Базовый урон: случайное значение между min_damage и max_damage
        min_dmg = attacker_unit['min_damage']
        max_dmg = attacker_unit['max_damage']
        base_damage = random.randint(min_dmg, max_dmg)
        damage_variance = 1.0  # Уже учтено в random.randint
        base_damage_with_variance = base_damage

        # Модификатор усталости на базовый урон (усталость снижает урон до -30%)
        fatigue_penalty = float(attacker.fatigue) / 100 * 0.3
        fatigue_modifier = 1.0 - fatigue_penalty

        # Модификатор куража (morale: 100 = 1.0, 110 = 1.1, 90 = 0.9)
        morale_modifier = float(attacker.morale) / 100

        # Применяем модификаторы к базовому урону
        damage = int(base_damage_with_variance * fatigue_modifier * morale_modifier)

        # Модификатор критического шанса (кураж увеличивает, усталость уменьшает)
        base_crit_chance = float(attacker_unit['crit_chance'])
        crit_modifier = base_crit_chance
        crit_modifier += float(attacker.morale) / 100 * 0.2  # До +20% от куража
        crit_modifier -= float(attacker.fatigue) / 100 * 0.2  # До -20% от усталости
        crit_modifier = max(0, min(1, crit_modifier))

        # Проверка критического удара
        crit_roll = random.random()
        is_crit = crit_roll < crit_modifier

        # Модификатор удачи (максимальный урон)
        luck_modifier = float(attacker_unit['luck'])
        luck_roll = random.random()
        is_lucky = luck_roll < luck_modifier

        # Хранение урона до модификаторов для лога
        damage_before_modifiers = damage

        if is_crit:
            damage = int(damage * 2)  # Критический удар удваивает урон

        if is_lucky:
            damage = int(damage * 1.5)  # Удача увеличивает урон на 50%

        # Умножить на количество атакующих юнитов
        damage_multiplied = damage * alive_attackers

        # Вычислить задетые юниты (сколько юнитов получит урон)
        # Формула: задетые_юниты = 1 + floor(0.5 * (dmg_multiplied - target_health) / target_health)
        import math
        target_health = target_unit['health']
        if damage_multiplied > target_health:
            affected_units = 1 + math.floor((0.5 * (damage_multiplied - target_health)) / target_health)
        else:
            affected_units = 1  # Если урон меньше здоровья одного юнита, задевается только 1

        # Применить защиту (вычитаем защиту × абсолютное значение задетых юнитов)
        alive_defenders = self._count_alive_units(target)
        defense_reduction = target_unit['defense'] * abs(affected_units)
        total_damage = damage_multiplied - defense_reduction

        # Создать детальный лог с формулой расчета
        attacker_display = f"x{actual_attackers}" if not is_kamikaze else f"x{actual_attackers} 💣КАМИКАДЗЕ💣"
        log = f"⚔️ {attacker_unit['name']} ({attacker_display}) атакует {target_unit['name']}\n"
        if is_kamikaze:
            log += f"⚠️ КАМИКАДЗЕ: урон рассчитывается только за 1 юнита (вместо {actual_attackers})\n"
        log += f"\n📊 Расчет урона:\n"
        log += f"1️⃣ Базовый урон: {min_dmg}-{max_dmg} → {base_damage}\n"

        if attacker.fatigue > 0:
            log += f"2️⃣ Усталость: {float(attacker.fatigue):.1f}% → штраф -{fatigue_penalty*100:.1f}% (x{fatigue_modifier:.2f})\n"

        if attacker.morale != 100:
            morale_display = "повышен" if attacker.morale > 100 else "понижен"
            log += f"3️⃣ Кураж: {morale_display} (x{morale_modifier:.2f})\n"

        log += f"   = {damage_before_modifiers} урона\n"

        # Информация о критическом ударе
        log += f"\n4️⃣ Шанс крита: {base_crit_chance*100:.1f}%"
        if attacker.morale > 0 or attacker.fatigue > 0:
            log += f" → {crit_modifier*100:.1f}%"
        log += f" (бросок: {crit_roll*100:.1f}%)\n"

        if is_crit:
            log += f"   💥 КРИТИЧЕСКИЙ УДАР! x2 = {damage} урона\n"

        # Информация об удаче
        log += f"5️⃣ Шанс удачи: {luck_modifier*100:.1f}% (бросок: {luck_roll*100:.1f}%)\n"
        if is_lucky:
            log += f"   🍀 УДАЧА! x1.5 = {damage} урона\n"

        # Умножение на количество атакующих
        log += f"\n6️⃣ Количество атакующих: x{alive_attackers}\n"
        log += f"   Урон до защиты: {damage_multiplied}\n"

        # Вычисление задетых юнитов
        log += f"\n7️⃣ Задетые юниты: 1 + floor(0.5 * ({damage_multiplied} - {target_health}) / {target_health}) = {affected_units}\n"

        # Защита
        log += f"\n8️⃣ Защита цели: {target_unit['defense']} × |{affected_units}| = {defense_reduction}\n"
        log += f"   Урон после защиты: {damage_multiplied} - {defense_reduction} = {total_damage}\n"
        log += f"   ⚡ ИТОГОВЫЙ УРОН: {int(total_damage)}"

        return total_damage, is_crit, log

    def _apply_damage(self, target: BattleUnit, damage: int) -> int:
        """
        Применить урон к юниту

        Args:
            target: Цель
            damage: Урон

        Returns:
            int: Количество убитых юнитов
        """
        target_unit = self._get_unit_stats(target)
        units_killed = 0

        while damage > 0 and target.total_count > 0:
            if damage >= target.remaining_hp:
                # Убить текущего юнита
                damage -= target.remaining_hp
                target.total_count -= 1
                units_killed += 1

                # Если все юниты убиты, remaining_hp = 0
                # Иначе восстанавливаем HP для следующего юнита
                if target.total_count > 0:
                    target.remaining_hp = target_unit['health']
                else:
                    target.remaining_hp = 0
            else:
                # Уменьшить HP текущего юнита
                target.remaining_hp -= damage
                damage = 0

        return units_killed

    def _count_alive_units(self, battle_unit: BattleUnit) -> int:
        """
        Подсчитать живых юнитов в группе

        Args:
            battle_unit: Юнит в бою

        Returns:
            int: Количество живых юнитов
        """
        if battle_unit.total_count == 0:
            return 0

        # Если есть юниты и у последнего есть HP
        if battle_unit.total_count > 0 and battle_unit.remaining_hp > 0:
            return battle_unit.total_count

        return 0

    def _get_available_targets(self, game: Game, attacker: BattleUnit) -> List[Dict]:
        """
        Получить доступные цели для атаки

        Args:
            game: Игра
            attacker: Атакующий юнит

        Returns:
            List[Dict]: Список доступных целей
        """
        attacker_unit = self._get_unit_stats(attacker)
        targets = []

        enemy_units = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game.id,
            BattleUnit.player_id != attacker.player_id
        ).all()

        for enemy in enemy_units:
            if self._count_alive_units(enemy) == 0:
                continue

            distance = abs(attacker.position_x - enemy.position_x) + abs(attacker.position_y - enemy.position_y)
            if distance <= attacker_unit['range']:
                # Проверить линию видимости до цели
                if self._has_line_of_sight(attacker.position_x, attacker.position_y,
                                           enemy.position_x, enemy.position_y, game):
                    enemy_unit = self._get_unit_stats(enemy)
                    targets.append({
                        "unit_id": enemy.id,
                        "unit_name": enemy_unit['name'],
                        "position": (enemy.position_x, enemy.position_y),
                        "distance": distance
                    })

        return targets

    def _all_units_moved(self, game: Game, player_id: int) -> bool:
        """
        Проверить, все ли юниты игрока походили

        Args:
            game: Игра
            player_id: ID игрока

        Returns:
            bool: True, если все походили
        """
        unmoved = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game.id,
            BattleUnit.player_id == player_id,
            BattleUnit.has_moved == 0
        ).count()

        return unmoved == 0

    def _switch_turn(self, game: Game):
        """
        Переключить ход на другого игрока

        Args:
            game: Игра
        """
        # Сменить игрока
        if game.current_player_id == game.player1_id:
            game.current_player_id = game.player2_id
        else:
            game.current_player_id = game.player1_id

        # Сбросить флаги has_moved и deferred для всех юнитов нового игрока
        units = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game.id,
            BattleUnit.player_id == game.current_player_id
        ).all()

        for unit in units:
            unit.has_moved = 0
            unit.deferred = 0

        # Применить эффекты начала хода для всех юнитов нового игрока
        self._apply_turn_start_effects(game, game.current_player_id)

        # Добавить запись в лог о смене хода
        current_player = self.db.query(GameUser).filter_by(id=game.current_player_id).first()
        player_name = current_player.username if current_player else "Игрок"
        self._log_event(game.id, "turn_switch", f"🔄 Ход переходит к {player_name}")

    def _apply_turn_start_effects(self, game: Game, player_id: int):
        """
        Применить эффекты начала хода для всех юнитов игрока (регенерация и яд)

        Args:
            game: Игра
            player_id: ID игрока
        """
        units = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game.id,
            BattleUnit.player_id == player_id
        ).all()

        for battle_unit in units:
            if battle_unit.total_count <= 0:
                continue

            unit_type = self._get_unit_stats(battle_unit)

            # Применить регенерацию
            regeneration = unit_type.get('regeneration_health', 0) or 0
            if regeneration > 0:
                self._apply_regeneration(battle_unit, regeneration)

            # Применить яд
            if battle_unit.poison_remaining_turns > 0:
                self._apply_poison_damage(game, battle_unit)

    def _apply_regeneration(self, battle_unit: BattleUnit, regeneration_health: int):
        """
        Применить регенерацию к юниту (увеличить количество юнитов)

        Args:
            battle_unit: Юнит в бою
            regeneration_health: Количество здоровья для регенерации
        """
        if battle_unit.total_count <= 0 or regeneration_health <= 0:
            return

        unit_type = self._get_unit_stats(battle_unit)
        max_health = unit_type['health']

        # Добавляем здоровье к remaining_hp
        old_hp = battle_unit.remaining_hp
        old_count = battle_unit.total_count

        # Регенерация добавляет HP
        new_hp = battle_unit.remaining_hp + regeneration_health

        # Если HP превышает максимум одного юнита, добавляем новых юнитов
        if new_hp > max_health:
            extra_units = new_hp // max_health
            battle_unit.total_count += extra_units
            battle_unit.remaining_hp = new_hp % max_health
            if battle_unit.remaining_hp == 0:
                battle_unit.remaining_hp = max_health
                battle_unit.total_count -= 1
        else:
            battle_unit.remaining_hp = new_hp

        # Логирование регенерации
        if battle_unit.total_count > old_count or battle_unit.remaining_hp > old_hp:
            units_gained = battle_unit.total_count - old_count
            hp_gained = battle_unit.remaining_hp - old_hp if battle_unit.total_count == old_count else regeneration_health
            logger.info(f"Регенерация: {unit_type['name']} восстановил {regeneration_health} HP (+{units_gained} юнитов)")

    def _apply_poison_damage(self, game: Game, battle_unit: BattleUnit):
        """
        Применить урон от яда к юниту

        Args:
            game: Игра
            battle_unit: Юнит в бою
        """
        if battle_unit.poison_remaining_turns <= 0 or battle_unit.poison_damage_per_turn <= 0:
            return

        unit_type = self._get_unit_stats(battle_unit)
        poison_damage = battle_unit.poison_damage_per_turn

        # Применить урон от яда
        units_killed = self._apply_damage(battle_unit, poison_damage)

        # Уменьшить счетчик ходов яда
        battle_unit.poison_remaining_turns -= 1

        # Логирование
        log_msg = f"☠️ ЯД: {unit_type['name']} получает {poison_damage} урона от отравления"
        if units_killed > 0:
            log_msg += f", погибло юнитов: {units_killed}"
        if battle_unit.poison_remaining_turns > 0:
            log_msg += f" (осталось ходов: {battle_unit.poison_remaining_turns})"
        else:
            log_msg += " (яд рассеялся)"

        self._log_event(game.id, "poison", log_msg)

        # Удалить юнит, если все погибли
        if battle_unit.total_count <= 0:
            logger.info(f"Удаление мёртвого юнита от яда: id={battle_unit.id}")
            self.db.delete(battle_unit)

    def _apply_poison_effect(self, attacker: BattleUnit, target: BattleUnit) -> str:
        """
        Применить эффект отравления при атаке

        Args:
            attacker: Атакующий юнит
            target: Цель

        Returns:
            str: Сообщение о применении яда
        """
        attacker_unit = self._get_unit_stats(attacker)
        target_unit = self._get_unit_stats(target)

        # Проверить, есть ли у атакующего способность отравления
        poison_damage = attacker_unit.get('poison_damage', 0) or 0
        poison_turns = attacker_unit.get('poison_turns', 0) or 0

        if poison_damage <= 0 or poison_turns <= 0:
            return ""

        # Проверить иммунитет к яду у цели
        poison_immunity = target_unit.get('poison_immunity', False)
        if poison_immunity:
            return f"\n\n🛡️ {target_unit['name']} имеет иммунитет к яду!"

        # Применить отравление к цели
        target.poison_damage_per_turn = poison_damage
        target.poison_remaining_turns = poison_turns

        return f"\n\n☠️ ОТРАВЛЕНИЕ! {target_unit['name']} отравлен на {poison_turns} ходов ({poison_damage} урона/ход)"

    def _check_game_over(self, game: Game) -> Optional[int]:
        """
        Проверить, окончена ли игра

        Args:
            game: Игра

        Returns:
            Optional[int]: ID победителя или None
        """
        # Проверить живых юнитов каждого игрока
        player1_alive = False
        player2_alive = False
        player1_units_count = 0
        player2_units_count = 0

        for battle_unit in game.battle_units:
            alive_count = self._count_alive_units(battle_unit)
            if alive_count > 0:
                if battle_unit.player_id == game.player1_id:
                    player1_alive = True
                    player1_units_count += alive_count
                else:
                    player2_alive = True
                    player2_units_count += alive_count

        logger.info(f"Проверка окончания игры #{game.id}: Player1 alive={player1_alive} ({player1_units_count} units), Player2 alive={player2_alive} ({player2_units_count} units)")

        if not player1_alive and player2_alive:
            logger.info(f"Игра #{game.id} окончена! Победитель: Player2 (ID: {game.player2_id})")
            return game.player2_id
        elif not player2_alive and player1_alive:
            logger.info(f"Игра #{game.id} окончена! Победитель: Player1 (ID: {game.player1_id})")
            return game.player1_id

        return None

    def surrender_game(self, game_id: int, player_id: int) -> Tuple[bool, str, Optional[int]]:
        """
        Выход из игры (сдаться) или отклонение вызова

        Args:
            game_id: ID игры
            player_id: ID игрока, который сдается или отклоняет вызов

        Returns:
            Tuple[bool, str, int]: Успех, сообщение, telegram_id противника
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return False, "Игра не найдена", None

        if game.status not in [GameStatus.WAITING, GameStatus.IN_PROGRESS]:
            return False, "Игра уже завершена", None

        # Проверить, что игрок участвует в игре
        if game.player1_id != player_id and game.player2_id != player_id:
            return False, "Вы не участвуете в этой игре", None

        # Определить победителя и проигравшего
        loser_id = player_id
        winner_id = game.player1_id if loser_id == game.player2_id else game.player2_id

        # Получить telegram_id противника для уведомления
        winner = self.db.query(GameUser).filter_by(id=winner_id).first()
        opponent_telegram_id = winner.telegram_id if winner else None

        # Получить имя сдавшегося игрока
        loser = self.db.query(GameUser).filter_by(id=loser_id).first()
        loser_name = loser.username if loser else "Unknown"

        # Если игра еще не началась (WAITING) - просто отменяем без наград и статистики
        if game.status == GameStatus.WAITING:
            # Удалить battle units
            self.db.query(BattleUnit).filter_by(game_id=game_id).delete()

            # Удалить препятствия
            self.db.query(Obstacle).filter_by(game_id=game_id).delete()

            # Удалить игру
            self.db.delete(game)
            self.db.commit()

            message = f"Вызов на бой отклонен"
            return True, message, opponent_telegram_id

        # Если игра в процессе (IN_PROGRESS) - завершить с начислением наград победителю
        reward, stats = self._complete_game(game, winner_id)

        self.db.commit()

        message = f"Вы сдались в игре #{game_id}. Урон юнитов зафиксирован. {winner.username} получил {format_coins(reward)} награды."
        return True, message, opponent_telegram_id

    def _save_battle_units_damage(self, game: Game):
        """
        Сохранить урон юнитов после завершения игры

        Args:
            game: Игра
        """
        units_to_delete = []
        for battle_unit in game.battle_units:
            # Подсчитать живых юнитов
            alive_count = self._count_alive_units(battle_unit)

            # Обновить количество юнитов в армии
            army_unit = battle_unit.army_unit
            unit_stats = self._get_unit_stats(battle_unit)
            old_count = army_unit.count
            army_unit.count = alive_count

            logger.info(f"Обновление юнитов после игры: {unit_stats['name']} игрока (ID: {battle_unit.player_id}) - было {old_count}, стало {alive_count}, потеряно {old_count - alive_count}")

            # Помечаем записи с count=0 для удаления
            if alive_count == 0:
                units_to_delete.append(army_unit)

        # Удаляем записи о юнитах с количеством 0
        for army_unit in units_to_delete:
            self.db.delete(army_unit)

        self.db.flush()

    def _complete_game(self, game: Game, winner_id: int) -> Tuple[Decimal, dict]:
        """
        Завершить игру

        Args:
            game: Игра
            winner_id: ID победителя

        Returns:
            Tuple[Decimal, dict]: Награда победителя в деньгах и статистика боя
        """
        from decimal import Decimal

        logger.info(f"🏆 Завершение игры #{game.id}, победитель ID: {winner_id}")

        game.status = GameStatus.COMPLETED
        game.winner_id = winner_id
        game.completed_at = datetime.utcnow()

        # Обновить статистику игроков
        winner = self.db.query(GameUser).filter_by(id=winner_id).first()
        loser_id = game.player1_id if winner_id == game.player2_id else game.player2_id
        loser = self.db.query(GameUser).filter_by(id=loser_id).first()

        logger.info(f"Победитель: {winner.username} (ID: {winner_id}), Проигравший: {loser.username} (ID: {loser_id})")

        # Обновляем статистику
        old_winner_wins = winner.wins
        old_loser_losses = loser.losses
        old_winner_balance = float(winner.balance)

        winner.wins += 1
        loser.losses += 1

        # Рассчитать награду (90% от стоимости побежденных юнитов) ДО сохранения урона
        killed_enemy_value = Decimal('0')  # Стоимость убитых юнитов противника
        lost_own_value = Decimal('0')  # Стоимость потерянных своих юнитов
        killed_enemy_details = []
        lost_own_details = []

        # Подсчитать убитых юнитов у обоих игроков
        for battle_unit in game.battle_units:
            unit_stats = self._get_unit_stats(battle_unit)
            unit_price = unit_stats['price']
            unit_name = unit_stats['name']
            initial_count = battle_unit.army_unit.count
            alive_count = self._count_alive_units(battle_unit)
            killed_count = initial_count - alive_count

            if killed_count > 0:
                unit_value = Decimal(str(unit_price)) * killed_count

                if battle_unit.player_id == loser_id:
                    # Юниты проигравшего
                    killed_enemy_value += unit_value
                    killed_enemy_details.append(f"{unit_name} x{killed_count} = {format_coins(unit_value)}")
                elif battle_unit.player_id == winner_id:
                    # Юниты победителя
                    lost_own_value += unit_value
                    lost_own_details.append(f"{unit_name} x{killed_count} = {format_coins(unit_value)}")

        # Награда = 70% от стоимости убитых юнитов противника + 100% стоимости потерянных своих юнитов
        reward = killed_enemy_value * Decimal('0.7') + lost_own_value

        # Чистая прибыль = Награда - Стоимость потерянных юнитов = 70% от убитых (так как свои потери компенсированы)
        net_profit = killed_enemy_value * Decimal('0.7')

        winner.balance += reward

        # Сохранить урон юнитов ПОСЛЕ расчета награды
        self._save_battle_units_damage(game)

        logger.info(f"📊 Статистика обновлена:")
        logger.info(f"  • {winner.username}: Побед {old_winner_wins} → {winner.wins}, Баланс {old_winner_balance:.2f} → {float(winner.balance):.2f} монет (+{float(reward):.2f})")
        logger.info(f"  • {loser.username}: Поражений {old_loser_losses} → {loser.losses}")
        logger.info(f"\n💰 Финансовая статистика:")
        if killed_enemy_details:
            logger.info(f"  • Убито юнитов противника ({loser.username}): {', '.join(killed_enemy_details)}")
            logger.info(f"    Общая стоимость: {float(killed_enemy_value):.2f} монет")
        if lost_own_details:
            logger.info(f"  • Потеряно своих юнитов ({winner.username}): {', '.join(lost_own_details)}")
            logger.info(f"    Общая стоимость: {float(lost_own_value):.2f} монет")
        logger.info(f"  • Награда (70% от убитых + 100% своих потерь): {float(reward):.2f} монет")
        logger.info(f"  • Чистая прибыль (70% от убитых): {float(net_profit):.2f} монет")

        # Логировать завершение игры с полной статистикой
        game_end_log = f"🏆 Игра завершена! Победитель: {winner.username}\n\n"
        game_end_log += f"💰 Финансовая статистика:\n"
        game_end_log += f"   📦 Убито юнитов {loser.username}: {format_coins(killed_enemy_value)}\n"
        if lost_own_value > 0:
            game_end_log += f"   ⚰️ Потеряно своих юнитов: {format_coins(lost_own_value)}\n"
        game_end_log += f"   💵 Награда (70% + потери): +{format_coins(reward)}"
        self._log_event(game.id, "game_ended", game_end_log)

        self.db.commit()
        logger.info(f"✅ Игра #{game.id} успешно завершена")

        # Вернуть награду и статистику
        stats = {
            'killed_enemy_value': killed_enemy_value,
            'lost_own_value': lost_own_value,
            'net_profit': net_profit,
            'killed_enemy_details': killed_enemy_details,
            'lost_own_details': lost_own_details
        }

        return reward, stats
