#!/usr/bin/env python3
"""
Игровой движок для обработки игровой логики
"""

import random
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session
from db.models import Game, GameStatus, BattleUnit, GameUser, UserUnit, Field, Unit


class GameEngine:
    """Класс для обработки игровой логики"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_game(self, player1_id: int, player2_username: str, field_name: str = "5x5") -> Tuple[Optional[Game], str]:
        """
        Создание новой игры

        Args:
            player1_id: ID игрока, создающего игру
            player2_username: Имя второго игрока
            field_name: Название поля (по умолчанию "5x5")

        Returns:
            Tuple[Game, str]: Созданная игра и сообщение
        """
        # Найти игроков
        player1 = self.db.query(GameUser).filter_by(id=player1_id).first()
        if not player1:
            return None, "Игрок 1 не найден"

        player2 = self.db.query(GameUser).filter_by(name=player2_username).first()
        if not player2:
            return None, f"Игрок с никнеймом '{player2_username}' не найден"

        if player1.id == player2.id:
            return None, "Нельзя играть с самим собой"

        # Проверить, что у обоих игроков есть юниты
        player1_units = self.db.query(UserUnit).filter(
            UserUnit.game_user_id == player1.id,
            UserUnit.count > 0
        ).all()
        player2_units = self.db.query(UserUnit).filter(
            UserUnit.game_user_id == player2.id,
            UserUnit.count > 0
        ).all()

        if not player1_units:
            return None, "У вас нет юнитов для игры"
        if not player2_units:
            return None, f"У игрока {player2_username} нет юнитов для игры"

        # Найти или создать поле
        field = self.db.query(Field).filter_by(name=field_name).first()
        if not field:
            # Создать стандартные поля, если их нет
            self._create_default_fields()
            field = self.db.query(Field).filter_by(name=field_name).first()
            if not field:
                return None, f"Поле '{field_name}' не найдено"

        # Создать игру
        game = Game(
            player1_id=player1.id,
            player2_id=player2.id,
            field_id=field.id,
            status=GameStatus.WAITING
        )
        self.db.add(game)
        self.db.flush()

        # Разместить юниты игроков на поле
        self._place_units(game, player1, player1_units, 1)
        self._place_units(game, player2, player2_units, 2)

        self.db.commit()
        return game, f"Игра создана! Ожидание принятия игроком {player2_username}"

    def accept_game(self, game_id: int, player_id: int) -> Tuple[bool, str]:
        """
        Принятие игры вторым игроком

        Args:
            game_id: ID игры
            player_id: ID игрока, принимающего игру

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

        # Начать игру
        game.status = GameStatus.IN_PROGRESS
        game.started_at = datetime.utcnow()
        game.current_player_id = game.player1_id  # Первый игрок ходит первым
        game.last_move_at = datetime.utcnow()

        self.db.commit()
        return True, "Игра начата! Ходит первый игрок"

    def move_unit(self, game_id: int, player_id: int, battle_unit_id: int, target_x: int, target_y: int) -> Tuple[bool, str]:
        """
        Перемещение юнита

        Args:
            game_id: ID игры
            player_id: ID игрока
            battle_unit_id: ID юнита в бою
            target_x: Целевая координата X
            target_y: Целевая координата Y

        Returns:
            Tuple[bool, str]: Успех и сообщение
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return False, "Игра не найдена"

        if game.status != GameStatus.IN_PROGRESS:
            return False, "Игра не в процессе"

        if game.current_player_id != player_id:
            return False, "Сейчас не ваш ход"

        battle_unit = self.db.query(BattleUnit).filter_by(id=battle_unit_id, game_id=game_id).first()
        if not battle_unit:
            return False, "Юнит не найден"

        if battle_unit.player_id != player_id:
            return False, "Это не ваш юнит"

        if battle_unit.has_moved:
            return False, "Этот юнит уже совершил ход"

        # Проверить, что цель в пределах поля
        if target_x < 0 or target_x >= game.field.width or target_y < 0 or target_y >= game.field.height:
            return False, "Цель за пределами поля"

        # Проверить, что цель свободна
        occupied = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game_id,
            BattleUnit.position_x == target_x,
            BattleUnit.position_y == target_y
        ).first()
        if occupied:
            return False, "Эта позиция занята"

        # Получить характеристики юнита
        unit = battle_unit.user_unit.unit

        # Проверить дистанцию (манхэттенское расстояние)
        distance = abs(battle_unit.position_x - target_x) + abs(battle_unit.position_y - target_y)
        if distance > unit.speed:
            return False, f"Слишком далеко! Скорость юнита: {unit.speed}, расстояние: {distance}"

        # Переместить юнита
        old_pos = (battle_unit.position_x, battle_unit.position_y)
        battle_unit.position_x = target_x
        battle_unit.position_y = target_y
        battle_unit.has_moved = 1

        # Проверить, все ли юниты текущего игрока походили
        if self._all_units_moved(game, player_id):
            self._switch_turn(game)

        game.last_move_at = datetime.utcnow()
        self.db.commit()

        return True, f"Юнит перемещен с {old_pos} на ({target_x}, {target_y})"

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
        unit = battle_unit.user_unit.unit
        speed = unit.speed
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

    def attack(self, game_id: int, player_id: int, attacker_id: int, target_id: int) -> Tuple[bool, str]:
        """
        Атака юнита

        Args:
            game_id: ID игры
            player_id: ID игрока
            attacker_id: ID атакующего юнита
            target_id: ID цели

        Returns:
            Tuple[bool, str]: Успех и сообщение с подробностями атаки
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return False, "Игра не найдена"

        if game.status != GameStatus.IN_PROGRESS:
            return False, "Игра не в процессе"

        if game.current_player_id != player_id:
            return False, "Сейчас не ваш ход"

        attacker = self.db.query(BattleUnit).filter_by(id=attacker_id, game_id=game_id).first()
        if not attacker:
            return False, "Атакующий юнит не найден"

        if attacker.player_id != player_id:
            return False, "Это не ваш юнит"

        if attacker.has_moved:
            return False, "Этот юнит уже совершил ход"

        target = self.db.query(BattleUnit).filter_by(id=target_id, game_id=game_id).first()
        if not target:
            return False, "Цель не найдена"

        if target.player_id == player_id:
            return False, "Нельзя атаковать своих юнитов"

        # Проверить дистанцию
        attacker_unit = attacker.user_unit.unit
        distance = abs(attacker.position_x - target.position_x) + abs(attacker.position_y - target.position_y)
        if distance > attacker_unit.range:
            return False, f"Цель слишком далеко! Дальность атаки: {attacker_unit.range}, расстояние: {distance}"

        # Рассчитать урон
        damage, is_crit, combat_log = self._calculate_damage(attacker, target)

        # Применить урон
        units_killed = self._apply_damage(target, damage)

        # Обновить мораль и усталость
        if is_crit or damage > 0:
            attacker.morale = min(float(attacker.morale) + 10, 100)
            attacker.fatigue = max(float(attacker.fatigue) - 5, 0)
        else:
            attacker.fatigue = min(float(attacker.fatigue) + 10, 100)
            attacker.morale = max(float(attacker.morale) - 5, 0)

        attacker.has_moved = 1

        # Проверить, все ли юниты игрока мертвы
        winner_id = self._check_game_over(game)
        if winner_id:
            self._complete_game(game, winner_id)
            winner_name = game.player1.name if winner_id == game.player1_id else game.player2.name
            combat_log += f"\n\n🏆 Игра окончена! Победитель: {winner_name}"
        else:
            # Проверить, все ли юниты текущего игрока походили
            if self._all_units_moved(game, player_id):
                self._switch_turn(game)

        game.last_move_at = datetime.utcnow()
        self.db.commit()

        result_msg = f"Атака выполнена!\n{combat_log}\nУбито юнитов: {units_killed}"
        return True, result_msg

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
            unit = battle_unit.user_unit.unit

            # Подсчитать живых юнитов
            alive_count = self._count_alive_units(battle_unit)

            if alive_count > 0:
                icon = unit.icon
                grid[y][x] = f"[{icon}{alive_count}]"

        # Собрать поле в строку
        result = f"Игра #{game.id} - {game.player1.name} vs {game.player2.name}\n"
        result += f"Статус: {game.status.value}\n"

        if game.status == GameStatus.IN_PROGRESS:
            current_player = game.player1.name if game.current_player_id == game.player1_id else game.player2.name
            result += f"Ход игрока: {current_player}\n"

        result += "\n"

        for y in range(height):
            result += "".join(grid[y]) + "\n"

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

        # Получить юниты игрока, которые еще не походили
        available_units = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game_id,
            BattleUnit.player_id == player_id,
            BattleUnit.has_moved == 0
        ).all()

        actions = []
        for unit in available_units:
            alive_count = self._count_alive_units(unit)
            if alive_count > 0:
                unit_type = unit.user_unit.unit
                actions.append({
                    "unit_id": unit.id,
                    "unit_name": unit_type.name,
                    "position": (unit.position_x, unit.position_y),
                    "can_move": True,
                    "targets": self._get_available_targets(game, unit)
                })

        return {"action": "play", "units": actions}

    # Вспомогательные методы

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

    def _place_units(self, game: Game, player: GameUser, user_units: List[UserUnit], side: int):
        """
        Разместить юниты игрока на поле

        Args:
            game: Игра
            player: Игрок
            user_units: Список юнитов игрока
            side: Сторона (1 или 2)
        """
        field = game.field

        # Определить стартовые позиции
        if side == 1:
            # Игрок 1 - левая сторона
            positions = [(0, y) for y in range(min(len(user_units), field.height))]
        else:
            # Игрок 2 - правая сторона
            positions = [(field.width - 1, y) for y in range(min(len(user_units), field.height))]

        for i, user_unit in enumerate(user_units[:len(positions)]):
            x, y = positions[i]
            unit_type = user_unit.unit

            battle_unit = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit.id,
                player_id=player.id,
                position_x=x,
                position_y=y,
                total_count=user_unit.count,
                remaining_hp=unit_type.health,
                morale=0,
                fatigue=0,
                has_moved=0
            )
            self.db.add(battle_unit)

    def _calculate_damage(self, attacker: BattleUnit, target: BattleUnit) -> Tuple[int, bool, str]:
        """
        Рассчитать урон

        Args:
            attacker: Атакующий юнит
            target: Цель

        Returns:
            Tuple[int, bool, str]: Урон, критический удар, лог боя
        """
        attacker_unit = attacker.user_unit.unit
        target_unit = target.user_unit.unit

        # Базовый урон
        base_damage = attacker_unit.damage

        # Модификатор критического шанса (кураж увеличивает, усталость уменьшает)
        crit_modifier = float(attacker_unit.crit_chance)
        crit_modifier += float(attacker.morale) / 100 * 0.2  # До +20% от куража
        crit_modifier -= float(attacker.fatigue) / 100 * 0.2  # До -20% от усталости
        crit_modifier = max(0, min(1, crit_modifier))

        # Проверка критического удара
        is_crit = random.random() < crit_modifier

        # Модификатор удачи (максимальный урон)
        luck_modifier = float(attacker_unit.luck)
        is_lucky = random.random() < luck_modifier

        # Рассчитать итоговый урон
        damage = base_damage

        if is_crit:
            damage = int(damage * 2)  # Критический удар удваивает урон

        if is_lucky:
            damage = int(damage * 1.5)  # Удача увеличивает урон на 50%

        # Применить защиту
        defense_reduction = target_unit.defense
        damage = max(1, damage - defense_reduction)  # Минимум 1 урона

        # Умножить на количество атакующих юнитов
        alive_attackers = self._count_alive_units(attacker)
        total_damage = damage * alive_attackers

        # Создать лог
        log = f"⚔️ {attacker_unit.name} (x{alive_attackers}) атакует {target_unit.name}\n"
        log += f"Базовый урон: {base_damage}, Защита цели: {defense_reduction}\n"

        if is_crit:
            log += "💥 КРИТИЧЕСКИЙ УДАР!\n"
        if is_lucky:
            log += "🍀 УДАЧА!\n"

        log += f"Итоговый урон: {total_damage}"

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
        target_unit = target.user_unit.unit
        units_killed = 0

        while damage > 0 and target.total_count > 0:
            if damage >= target.remaining_hp:
                # Убить текущего юнита
                damage -= target.remaining_hp
                target.total_count -= 1
                units_killed += 1
                target.remaining_hp = target_unit.health
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
        attacker_unit = attacker.user_unit.unit
        targets = []

        enemy_units = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game.id,
            BattleUnit.player_id != attacker.player_id
        ).all()

        for enemy in enemy_units:
            if self._count_alive_units(enemy) == 0:
                continue

            distance = abs(attacker.position_x - enemy.position_x) + abs(attacker.position_y - enemy.position_y)
            if distance <= attacker_unit.range:
                targets.append({
                    "unit_id": enemy.id,
                    "unit_name": enemy.user_unit.unit.name,
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

        # Сбросить флаги has_moved для всех юнитов нового игрока
        units = self.db.query(BattleUnit).filter(
            BattleUnit.game_id == game.id,
            BattleUnit.player_id == game.current_player_id
        ).all()

        for unit in units:
            unit.has_moved = 0

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

        for battle_unit in game.battle_units:
            if self._count_alive_units(battle_unit) > 0:
                if battle_unit.player_id == game.player1_id:
                    player1_alive = True
                else:
                    player2_alive = True

        if not player1_alive and player2_alive:
            return game.player2_id
        elif not player2_alive and player1_alive:
            return game.player1_id

        return None

    def _complete_game(self, game: Game, winner_id: int):
        """
        Завершить игру

        Args:
            game: Игра
            winner_id: ID победителя
        """
        game.status = GameStatus.COMPLETED
        game.winner_id = winner_id
        game.completed_at = datetime.utcnow()

        # Обновить статистику игроков
        winner = self.db.query(GameUser).filter_by(id=winner_id).first()
        loser_id = game.player1_id if winner_id == game.player2_id else game.player2_id
        loser = self.db.query(GameUser).filter_by(id=loser_id).first()

        winner.wins += 1
        loser.losses += 1

        # Рассчитать награду (стоимость побежденных юнитов)
        reward = 0
        for battle_unit in game.battle_units:
            if battle_unit.player_id == loser_id:
                unit_price = battle_unit.user_unit.unit.price
                # Награда за убитых юнитов
                original_count = battle_unit.user_unit.count
                killed_count = original_count - self._count_alive_units(battle_unit)
                reward += float(unit_price) * killed_count

        winner.balance += reward

        self.db.commit()
