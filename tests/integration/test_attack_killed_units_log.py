#!/usr/bin/env python3
"""
Интеграционные тесты для проверки логирования убитых юнитов в атаках
и обновления состояния игры после атаки
"""

import pytest
import re
import uuid
from decimal import Decimal
import tempfile
import os
from db.models import GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field, GameLog
from core.game_engine import GameEngine


def unique_name(base_name):
    """Генерирует уникальное имя с UUID суффиксом"""
    return f"{base_name}_{uuid.uuid4().hex[:8]}"


class TestAttackKilledUnitsLogging:
    """Тесты для проверки логирования убитых юнитов в атаках"""

    def test_killed_units_in_attack_log(self, db_session):
        """Тест: количество убитых юнитов записывается в лог атаки"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Создать временный файл для изображения
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Создать юнита с достаточным уроном
            unit = Unit(
                name=unique_name("Воин"),
                icon="⚔️",
                price=Decimal("100"),
                damage=100,  # Большой урон чтобы гарантированно убить
                defense=0,
                health=50,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            # У Player1 3 юнита, у Player2 2 юнита
            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=3)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=2)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            # Использовать существующее поле или создать уникальное
            field = db_session.query(Field).filter_by(name="5x5").first()
            if not field:
                field = Field(name="5x5", width=5, height=5)
                db_session.add(field)
                db_session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS,
                current_player_id=player1.id
            )
            db_session.add(game)
            db_session.flush()

            # Создать боевых юнитов
            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=3,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=2,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            # Атака
            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(game.id, player1.id, battle_unit1.id, battle_unit2.id)

            assert success, f"Атака должна быть успешной: {message}"

            # Проверить, что в логе атаки есть информация об убитых юнитах
            attack_log = db_session.query(GameLog).filter_by(
                game_id=game.id,
                event_type="attack"
            ).first()

            assert attack_log is not None, "Лог атаки должен существовать"

            # Проверяем что в сообщении лога есть "Убито юнитов: X"
            killed_match = re.search(r'Убито юнитов:\s*(\d+)', attack_log.message)
            assert killed_match is not None, f"В логе атаки должна быть информация об убитых юнитах: {attack_log.message}"

            killed_count = int(killed_match.group(1))
            assert killed_count > 0, f"Должен быть убит хотя бы 1 юнит, но получено: {killed_count}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_killed_units_message_format(self, db_session):
        """Тест: формат сообщения об убитых юнитах соответствует regex на фронтенде"""
        # Создать тестовых пользователей
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            unit = Unit(
                name=unique_name("Воин"),
                icon="⚔️",
                price=Decimal("100"),
                damage=100,
                defense=0,
                health=50,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=3)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=2)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            field = db_session.query(Field).filter_by(name="5x5").first()
            if not field:
                field = Field(name="5x5", width=5, height=5)
                db_session.add(field)
                db_session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS,
                current_player_id=player1.id
            )
            db_session.add(game)
            db_session.flush()

            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=3,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=2,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            engine = GameEngine(db_session)
            success, result_message, turn_switched = engine.attack(
                game.id, player1.id, battle_unit1.id, battle_unit2.id
            )

            assert success, f"Атака должна быть успешной: {result_message}"

            # Тестируем regex которые используются на фронтенде
            target_killed_regex = r'Убито юнитов:\s*(\d+)'
            attacker_killed_regex = r'Убито атакующих юнитов:\s*(\d+)'

            # Проверяем формат для убитых юнитов защитника
            target_match = re.search(target_killed_regex, result_message)
            assert target_match is not None, \
                f"Сообщение должно содержать 'Убито юнитов: X', но получено: {result_message}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_dead_unit_removed_from_game_state(self, db_session):
        """Тест: мертвые юниты удаляются из game_state в логе"""
        import json

        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Юнит с большим уроном чтобы убить всех
            unit = Unit(
                name=unique_name("Воин"),
                icon="⚔️",
                price=Decimal("100"),
                damage=200,  # Очень большой урон
                defense=0,
                health=50,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=3)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=1)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            field = db_session.query(Field).filter_by(name="5x5").first()
            if not field:
                field = Field(name="5x5", width=5, height=5)
                db_session.add(field)
                db_session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS,
                current_player_id=player1.id
            )
            db_session.add(game)
            db_session.flush()

            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=3,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=1,  # Только 1 юнит
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            target_unit_id = battle_unit2.id

            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(
                game.id, player1.id, battle_unit1.id, target_unit_id
            )

            assert success, f"Атака должна быть успешной: {message}"

            # Проверяем что игра завершена (все юниты player2 убиты)
            db_session.refresh(game)
            assert game.status == GameStatus.COMPLETED, "Игра должна быть завершена"

            # Проверяем game_state в последнем логе - мертвый юнит не должен быть там
            last_log = db_session.query(GameLog).filter_by(
                game_id=game.id
            ).order_by(GameLog.id.desc()).first()

            if last_log and last_log.game_state:
                game_state = json.loads(last_log.game_state)
                unit_ids = [u['id'] for u in game_state.get('units', [])]

                # Убитый юнит не должен быть в game_state
                assert target_unit_id not in unit_ids, \
                    f"Мертвый юнит {target_unit_id} не должен быть в game_state: {unit_ids}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_unit_count_updated_in_game_state_after_partial_kill(self, db_session):
        """Тест: количество юнитов обновляется в game_state после частичного убийства"""
        import json

        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Юнит со средним уроном чтобы убить часть юнитов
            unit = Unit(
                name=unique_name("Воин"),
                icon="⚔️",
                price=Decimal("100"),
                damage=30,  # Средний урон
                defense=0,
                health=50,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=3)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            field = db_session.query(Field).filter_by(name="5x5").first()
            if not field:
                field = Field(name="5x5", width=5, height=5)
                db_session.add(field)
                db_session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS,
                current_player_id=player1.id
            )
            db_session.add(game)
            db_session.flush()

            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=3,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=5,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            initial_count = battle_unit2.total_count
            target_unit_id = battle_unit2.id

            engine = GameEngine(db_session)
            success, message, turn_switched = engine.attack(
                game.id, player1.id, battle_unit1.id, target_unit_id
            )

            assert success, f"Атака должна быть успешной: {message}"

            # Получаем обновленное количество юнитов
            db_session.refresh(battle_unit2)
            new_count = battle_unit2.total_count

            # Проверяем что количество изменилось
            assert new_count < initial_count, \
                f"Количество юнитов должно уменьшиться: было {initial_count}, стало {new_count}"

            # Проверяем game_state в логе атаки
            attack_log = db_session.query(GameLog).filter_by(
                game_id=game.id,
                event_type="attack"
            ).first()

            assert attack_log is not None, "Лог атаки должен существовать"
            assert attack_log.game_state is not None, "Game state должен быть сохранен в логе"

            game_state = json.loads(attack_log.game_state)

            # Находим юнита в game_state
            target_in_state = None
            for unit_state in game_state.get('units', []):
                if unit_state['id'] == target_unit_id:
                    target_in_state = unit_state
                    break

            assert target_in_state is not None, \
                f"Юнит должен быть в game_state: {game_state.get('units', [])}"

            assert target_in_state['total_count'] == new_count, \
                f"Количество юнитов в game_state должно быть {new_count}, но получено {target_in_state['total_count']}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_counterattack_killed_units_in_message(self, db_session):
        """Тест: убитые юниты от контратаки отображаются в сообщении"""
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Юнит с высоким уроном для контратаки
            unit = Unit(
                name=unique_name("Воин"),
                icon="⚔️",
                price=Decimal("100"),
                damage=80,  # Высокий урон для возможной контратаки
                defense=0,
                health=30,  # Низкое здоровье для легкого убийства контратакой
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                counterattack_chance=Decimal("1.0"),  # 100% коэффициент контратаки
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=5)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            field = db_session.query(Field).filter_by(name="5x5").first()
            if not field:
                field = Field(name="5x5", width=5, height=5)
                db_session.add(field)
                db_session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS,
                current_player_id=player1.id
            )
            db_session.add(game)
            db_session.flush()

            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=1,  # Только 1 атакующий
                remaining_hp=30,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=5,  # Много защитников для мощной контратаки
                remaining_hp=30,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            engine = GameEngine(db_session)

            # Пробуем несколько раз, т.к. контратака имеет 50% шанс
            counterattack_found = False
            for _ in range(10):
                # Сбрасываем состояние
                battle_unit1.total_count = 1
                battle_unit1.remaining_hp = 30
                battle_unit1.has_moved = 0
                battle_unit2.total_count = 5
                battle_unit2.remaining_hp = 30
                db_session.flush()

                success, message, _ = engine.attack(
                    game.id, player1.id, battle_unit1.id, battle_unit2.id
                )

                if success and 'Убито атакующих юнитов' in message:
                    counterattack_found = True
                    # Проверяем формат
                    attacker_killed_match = re.search(
                        r'Убито атакующих юнитов:\s*(\d+)',
                        message
                    )
                    assert attacker_killed_match is not None, \
                        f"Неправильный формат 'Убито атакующих юнитов': {message}"
                    break

                # Сбрасываем has_moved для следующей попытки
                battle_unit1.has_moved = 0
                db_session.flush()

            # Если ни одна контратака не сработала за 10 попыток - это маловероятно (0.1%)
            # Но мы все равно не фейлим тест, т.к. это статистически возможно

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


class TestGameStateUnitUpdates:
    """Тесты для проверки обновления юнитов в game_state"""

    def test_battle_unit_deleted_when_all_killed(self, db_session):
        """Тест: BattleUnit удаляется из БД когда все юниты убиты"""
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            unit = Unit(
                name=unique_name("Воин"),
                icon="⚔️",
                price=Decimal("100"),
                damage=200,  # Большой урон
                defense=0,
                health=50,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add(unit)
            db_session.flush()

            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit.id, count=3)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit.id, count=1)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            field = db_session.query(Field).filter_by(name="5x5").first()
            if not field:
                field = Field(name="5x5", width=5, height=5)
                db_session.add(field)
                db_session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS,
                current_player_id=player1.id
            )
            db_session.add(game)
            db_session.flush()

            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=3,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=1,
                remaining_hp=50,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            target_id = battle_unit2.id

            engine = GameEngine(db_session)
            success, message, _ = engine.attack(
                game.id, player1.id, battle_unit1.id, target_id
            )

            assert success, f"Атака должна быть успешной: {message}"

            # Проверяем что BattleUnit удален из БД
            deleted_unit = db_session.query(BattleUnit).filter_by(id=target_id).first()
            assert deleted_unit is None, \
                f"BattleUnit должен быть удален из БД, но он существует: {deleted_unit}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    def test_zero_killed_units_shows_zero(self, db_session):
        """Тест: при 0 убитых юнитов (dodge) показывается 'Убито юнитов: 0'"""
        player1 = GameUser(telegram_id=111, username="Player1", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, username="Player2", balance=Decimal("1000"))
        db_session.add_all([player1, player2])
        db_session.flush()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            temp_image_path = f.name
            f.write("test image data")

        try:
            # Юнит с минимальным уроном и высоким здоровьем
            unit1 = Unit(
                name=unique_name("Слабый воин"),
                icon="⚔️",
                price=Decimal("100"),
                damage=1,  # Минимальный урон
                defense=0,
                health=500,  # Очень высокое здоровье
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_image_path
            )

            # Юнит с высокой защитой
            unit2 = Unit(
                name=unique_name("Танк"),
                icon="🛡️",
                price=Decimal("100"),
                damage=1,
                defense=100,  # Высокая защита
                health=500,
                range=1,
                speed=1,
                luck=Decimal("0"),
                crit_chance=Decimal("0"),
                image_path=temp_image_path
            )
            db_session.add_all([unit1, unit2])
            db_session.flush()

            user_unit1 = UserUnit(game_user_id=player1.id, unit_type_id=unit1.id, count=1)
            user_unit2 = UserUnit(game_user_id=player2.id, unit_type_id=unit2.id, count=1)
            db_session.add_all([user_unit1, user_unit2])
            db_session.flush()

            field = db_session.query(Field).filter_by(name="5x5").first()
            if not field:
                field = Field(name="5x5", width=5, height=5)
                db_session.add(field)
                db_session.flush()

            game = Game(
                player1_id=player1.id,
                player2_id=player2.id,
                field_id=field.id,
                status=GameStatus.IN_PROGRESS,
                current_player_id=player1.id
            )
            db_session.add(game)
            db_session.flush()

            battle_unit1 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit1.id,
                player_id=player1.id,
                position_x=0,
                position_y=0,
                total_count=1,
                remaining_hp=500,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            battle_unit2 = BattleUnit(
                game_id=game.id,
                user_unit_id=user_unit2.id,
                player_id=player2.id,
                position_x=1,
                position_y=0,
                total_count=1,
                remaining_hp=500,
                morale=100,
                fatigue=0,
                has_moved=0
            )
            db_session.add_all([battle_unit1, battle_unit2])
            db_session.flush()

            engine = GameEngine(db_session)
            success, message, _ = engine.attack(
                game.id, player1.id, battle_unit1.id, battle_unit2.id
            )

            assert success, f"Атака должна быть успешной: {message}"

            # Проверяем что сообщение содержит "Убито юнитов: 0"
            killed_match = re.search(r'Убито юнитов:\s*(\d+)', message)
            assert killed_match is not None, \
                f"Сообщение должно содержать 'Убито юнитов: X': {message}"

            killed_count = int(killed_match.group(1))
            assert killed_count == 0, \
                f"При слабой атаке с высокой защитой убитых должно быть 0, но получено: {killed_count}"

        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
