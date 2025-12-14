#!/usr/bin/env python3
"""
Интеграционные тесты для подбора противников по стоимости армии.
Проверяет корректность работы фильтрации по престижу армии (±50%).
"""

import pytest
import uuid
from decimal import Decimal
from db.models import (
    GameUser, GameRace, RaceUnit, UnitLevel,
    UserRace, Army, ArmyUnit
)


def unique_name(prefix):
    """Генерирует уникальное имя"""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_race(db_session):
    """Создает тестовую расу"""
    race = GameRace(name=unique_name("Раса"), description="Раса для тестов", is_free=True)
    db_session.add(race)
    db_session.flush()
    return race


@pytest.fixture
def unit_levels(db_session):
    """Получает или создает тестовые уровни юнитов"""
    levels = {}
    for level_num in [1, 2, 3]:
        level = db_session.query(UnitLevel).filter_by(level=level_num).first()
        if not level:
            prestige_values = {1: (0, 100), 2: (100, 300), 3: (300, 600)}
            p_min, p_max = prestige_values.get(level_num, (0, 100))
            level = UnitLevel(level=level_num, icon=f"L{level_num}", prestige_min=p_min, prestige_max=p_max)
            db_session.add(level)
            db_session.flush()
        levels[level_num] = level
    return levels


@pytest.fixture
def test_race_units(db_session, test_race, unit_levels):
    """Создает тестовых юнитов расы разных уровней"""
    units = {}
    for level_num, level in unit_levels.items():
        unit = RaceUnit(
            race_id=test_race.id,
            unit_level_id=level.id,
            name=unique_name(f"Юнит_L{level_num}"),
            attack=10 * level_num, defense=5 * level_num,
            min_damage=level_num, max_damage=level_num * 3,
            health=10 * level_num, speed=4, initiative=10,
            is_flying=False, is_kamikaze=False
        )
        db_session.add(unit)
        db_session.flush()
        units[level_num] = unit
    return units


class TestArmyValueCalculation:
    """Тесты для расчета стоимости армии"""

    def test_calculate_army_value_empty(self, db_session, db, test_race):
        """Проверка расчета стоимости пустой армии"""
        game_user = GameUser(
            telegram_id=111222333,
            username=unique_name("empty_army_user"),
            balance=1000.0
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        army = Army(user_race_id=user_race.id, name="Пустая армия", army_type="rated")
        db_session.add(army)
        db_session.commit()

        army_value = db._calculate_army_value(db_session, army)
        assert army_value == 0.0

    def test_calculate_army_value_with_units(self, db_session, db, test_race, unit_levels, test_race_units):
        """Проверка расчета стоимости армии с юнитами"""
        game_user = GameUser(
            telegram_id=222333444,
            username=unique_name("army_user"),
            balance=1000.0
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        army = Army(user_race_id=user_race.id, name="Тестовая армия", army_type="rated")
        db_session.add(army)
        db_session.flush()

        # Добавляем 10 юнитов 1 уровня
        army_unit = ArmyUnit(
            army_id=army.id,
            race_unit_id=test_race_units[1].id,
            unit_level_id=unit_levels[1].id,
            count=10
        )
        db_session.add(army_unit)
        db_session.commit()

        army_value = db._calculate_army_value(db_session, army)
        assert army_value > 0

    def test_army_value_scales_with_unit_count(self, db_session, db, test_race, unit_levels, test_race_units):
        """Проверка что стоимость армии увеличивается с количеством юнитов"""
        game_user = GameUser(
            telegram_id=333444555,
            username=unique_name("scale_user"),
            balance=1000.0
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        # Армия с 5 юнитами
        army1 = Army(user_race_id=user_race.id, name="Малая армия", army_type="rated")
        db_session.add(army1)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army1.id, race_unit_id=test_race_units[1].id,
                               unit_level_id=unit_levels[1].id, count=5))

        # Армия с 10 юнитами
        army2 = Army(user_race_id=user_race.id, name="Большая армия", army_type="rated")
        db_session.add(army2)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army2.id, race_unit_id=test_race_units[1].id,
                               unit_level_id=unit_levels[1].id, count=10))
        db_session.commit()

        value1 = db._calculate_army_value(db_session, army1)
        value2 = db._calculate_army_value(db_session, army2)

        assert value2 == value1 * 2  # 10 юнитов в 2 раза дороже чем 5

    def test_army_value_scales_with_prestige(self, db_session, db, test_race, unit_levels, test_race_units):
        """Проверка что стоимость армии зависит от престижа уровня юнита"""
        game_user = GameUser(
            telegram_id=444555666,
            username=unique_name("prestige_user"),
            balance=1000.0
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        # Армия с юнитами 1 уровня
        army1 = Army(user_race_id=user_race.id, name="Армия L1", army_type="rated")
        db_session.add(army1)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army1.id, race_unit_id=test_race_units[1].id,
                               unit_level_id=unit_levels[1].id, count=10))

        # Армия с юнитами 3 уровня (более высокий престиж)
        army3 = Army(user_race_id=user_race.id, name="Армия L3", army_type="rated")
        db_session.add(army3)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army3.id, race_unit_id=test_race_units[3].id,
                               unit_level_id=unit_levels[3].id, count=10))
        db_session.commit()

        value1 = db._calculate_army_value(db_session, army1)
        value3 = db._calculate_army_value(db_session, army3)

        # Юниты 3 уровня должны быть дороже из-за более высокого престижа и характеристик
        assert value3 > value1


class TestOpponentMatching:
    """Тесты для подбора противников по стоимости армии"""

    def test_opponent_matching_returns_tuple(self, db_session, db, test_race, unit_levels, test_race_units):
        """Проверка что метод возвращает tuple (player_data, opponents)"""
        game_user = GameUser(
            telegram_id=555666777,
            username=unique_name("tuple_user"),
            balance=1000.0
        )
        db_session.add(game_user)
        db_session.commit()

        result = db.get_available_opponents_by_username(game_user.username, limit=5, variance=0.5)

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_opponent_matching_player_data_has_army_value(self, db_session, db, test_race, unit_levels, test_race_units):
        """Проверка что данные текущего игрока содержат стоимость армии"""
        game_user = GameUser(
            telegram_id=666777888,
            username=unique_name("value_user"),
            balance=1000.0
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        army = Army(user_race_id=user_race.id, name="Армия", army_type="rated")
        db_session.add(army)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army.id, race_unit_id=test_race_units[1].id,
                               unit_level_id=unit_levels[1].id, count=10))
        db_session.commit()

        current_player, _ = db.get_available_opponents_by_username(game_user.username, limit=5, variance=0.5)

        assert current_player is not None
        assert 'army_value' in current_player
        assert current_player['army_value'] > 0

    def test_opponent_matching_filters_by_variance(self, db_session, db, test_race, unit_levels, test_race_units):
        """Проверка фильтрации противников по допустимой разнице в стоимости армии"""
        # Создаем текущего игрока со средней армией
        player1 = GameUser(telegram_id=777888999, username=unique_name("filter_player1"), balance=1000.0)
        db_session.add(player1)
        db_session.flush()
        ur1 = UserRace(user_id=player1.id, race_id=test_race.id)
        db_session.add(ur1)
        db_session.flush()
        army1 = Army(user_race_id=ur1.id, name="Армия P1", army_type="rated")
        db_session.add(army1)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army1.id, race_unit_id=test_race_units[2].id,
                               unit_level_id=unit_levels[2].id, count=10))

        # Создаем противника с очень слабой армией (должен быть отфильтрован)
        player2 = GameUser(telegram_id=888999000, username=unique_name("filter_player2"), balance=1000.0)
        db_session.add(player2)
        db_session.flush()
        ur2 = UserRace(user_id=player2.id, race_id=test_race.id)
        db_session.add(ur2)
        db_session.flush()
        army2 = Army(user_race_id=ur2.id, name="Армия P2", army_type="rated")
        db_session.add(army2)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army2.id, race_unit_id=test_race_units[1].id,
                               unit_level_id=unit_levels[1].id, count=1))  # очень маленькая армия

        # Создаем противника с похожей армией (должен быть найден)
        player3 = GameUser(telegram_id=999000111, username=unique_name("filter_player3"), balance=1000.0)
        db_session.add(player3)
        db_session.flush()
        ur3 = UserRace(user_id=player3.id, race_id=test_race.id)
        db_session.add(ur3)
        db_session.flush()
        army3 = Army(user_race_id=ur3.id, name="Армия P3", army_type="rated")
        db_session.add(army3)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army3.id, race_unit_id=test_race_units[2].id,
                               unit_level_id=unit_levels[2].id, count=9))  # похожая армия

        db_session.commit()

        # Запрашиваем противников с variance=0.5 (±50%)
        current_player, opponents = db.get_available_opponents_by_username(player1.username, limit=10, variance=0.5)

        assert current_player is not None
        opponent_usernames = [o['name'] for o in opponents]

        # Player3 должен быть в списке (похожая армия)
        # Player2 скорее всего не должен быть (очень маленькая армия)
        if opponents:
            for opp in opponents:
                # Проверяем что все противники в допустимом диапазоне
                min_value = current_player['army_value'] * 0.5
                max_value = current_player['army_value'] * 1.5
                assert opp['army_value'] >= min_value or current_player['army_value'] == 0
                assert opp['army_value'] <= max_value or current_player['army_value'] == 0

    def test_opponent_matching_excludes_self(self, db_session, db, test_race, unit_levels, test_race_units):
        """Проверка что текущий игрок не включается в список противников"""
        game_user = GameUser(
            telegram_id=111000222,
            username=unique_name("self_user"),
            balance=1000.0
        )
        db_session.add(game_user)
        db_session.flush()
        ur = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(ur)
        db_session.flush()
        army = Army(user_race_id=ur.id, name="Армия", army_type="rated")
        db_session.add(army)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army.id, race_unit_id=test_race_units[1].id,
                               unit_level_id=unit_levels[1].id, count=10))
        db_session.commit()

        _, opponents = db.get_available_opponents_by_username(game_user.username, limit=10, variance=1.0)

        opponent_ids = [o['id'] for o in opponents]
        assert game_user.id not in opponent_ids

    def test_opponent_matching_returns_none_for_unknown_user(self, db_session, db):
        """Проверка что возвращается None для несуществующего пользователя"""
        result, opponents = db.get_available_opponents_by_username("nonexistent_user_xyz", limit=5, variance=0.5)

        assert result is None
        assert opponents == []


class TestArmySelectionFeature:
    """Тесты для функции выбора армии при вызове на бой"""

    def test_current_player_has_username_field(self, db_session, db, test_race):
        """Проверка что данные текущего игрока содержат поле username"""
        game_user = GameUser(
            telegram_id=222111333,
            username=unique_name("username_user"),
            balance=1000.0
        )
        db_session.add(game_user)
        db_session.commit()

        current_player, _ = db.get_available_opponents_by_username(game_user.username, limit=5, variance=0.5)

        assert current_player is not None
        assert 'username' in current_player
        assert current_player['username'] == game_user.username

    def test_opponents_have_required_fields(self, db_session, db, test_race, unit_levels, test_race_units):
        """Проверка что данные противников содержат все необходимые поля"""
        # Создаем двух игроков с армиями
        player1 = GameUser(telegram_id=333222111, username=unique_name("fields_p1"), balance=1000.0)
        db_session.add(player1)
        db_session.flush()
        ur1 = UserRace(user_id=player1.id, race_id=test_race.id)
        db_session.add(ur1)
        db_session.flush()
        army1 = Army(user_race_id=ur1.id, name="Армия P1", army_type="rated")
        db_session.add(army1)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army1.id, race_unit_id=test_race_units[1].id,
                               unit_level_id=unit_levels[1].id, count=10))

        player2 = GameUser(telegram_id=444333222, username=unique_name("fields_p2"), balance=1000.0, wins=5, losses=3)
        db_session.add(player2)
        db_session.flush()
        ur2 = UserRace(user_id=player2.id, race_id=test_race.id)
        db_session.add(ur2)
        db_session.flush()
        army2 = Army(user_race_id=ur2.id, name="Армия P2", army_type="rated")
        db_session.add(army2)
        db_session.flush()
        db_session.add(ArmyUnit(army_id=army2.id, race_unit_id=test_race_units[1].id,
                               unit_level_id=unit_levels[1].id, count=10))
        db_session.commit()

        _, opponents = db.get_available_opponents_by_username(player1.username, limit=10, variance=1.0)

        if opponents:
            opp = opponents[0]
            required_fields = ['id', 'name', 'wins', 'losses', 'army_value', 'win_rate']
            for field in required_fields:
                assert field in opp, f"Missing field: {field}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
