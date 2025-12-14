#!/usr/bin/env python3
"""
Интеграционные тесты для отображения армий в профиле пользователя.
Проверяет корректность работы связей UserRace -> Army -> ArmyUnit -> RaceUnit.
"""

import pytest
import uuid
from db.models import (
    GameUser, GameRace, RaceUnit, UnitLevel,
    UserRace, UserRaceUnit, Army, ArmyUnit
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
def test_unit_level(db_session):
    """Получает или создает тестовый уровень юнита"""
    # Используем существующий уровень из seed data
    level = db_session.query(UnitLevel).filter_by(level=1).first()
    if level:
        return level
    # Если нет - создаем с уровнем 1 (единственный допустимый для нового)
    level = UnitLevel(level=1, icon="⚔️", prestige_min=0, prestige_max=100)
    db_session.add(level)
    db_session.flush()
    return level


@pytest.fixture
def test_race_unit(db_session, test_race, test_unit_level):
    """Создает тестового юнита расы"""
    unit = RaceUnit(
        race_id=test_race.id,
        unit_level_id=test_unit_level.id,
        name=unique_name("Воин"),
        attack=10, defense=8,
        min_damage=5, max_damage=10,
        health=50, speed=4, initiative=10,
        is_flying=False, is_kamikaze=False
    )
    db_session.add(unit)
    db_session.flush()
    return unit


class TestArmyProfileDisplay:
    """Тесты для отображения армий в профиле"""

    def test_create_user_with_race_and_army(self, db_session, test_race, test_unit_level, test_race_unit):
        """Проверка создания пользователя с расой и армией"""
        game_user = GameUser(
            telegram_id=123456789,
            username=unique_name("user"),
            balance=1000.0,
            crystals=100,
            glory=50,
            wins=5,
            losses=3
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        army = Army(user_race_id=user_race.id, name="Тестовая армия", army_type="rated")
        db_session.add(army)
        db_session.flush()

        army_unit = ArmyUnit(
            army_id=army.id,
            race_unit_id=test_race_unit.id,
            unit_level_id=test_unit_level.id,
            count=10
        )
        db_session.add(army_unit)
        db_session.commit()

        assert game_user.id is not None
        assert user_race.id is not None
        assert army.id is not None
        assert army_unit.id is not None

    def test_query_user_armies_with_composition(self, db_session, test_race, test_unit_level, test_race_unit):
        """Проверка запроса армий пользователя с составом"""
        game_user = GameUser(
            telegram_id=987654321,
            username=unique_name("profile_user"),
            balance=500.0,
            crystals=50,
            glory=25,
            wins=3,
            losses=2
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        army = Army(user_race_id=user_race.id, name="Армия профиля", army_type="mercenary")
        db_session.add(army)
        db_session.flush()

        army_unit = ArmyUnit(
            army_id=army.id,
            race_unit_id=test_race_unit.id,
            unit_level_id=test_unit_level.id,
            count=5
        )
        db_session.add(army_unit)
        db_session.commit()

        # Запрос как в profile_command
        user_races = db_session.query(UserRace).filter_by(user_id=game_user.id).all()
        assert len(user_races) == 1

        armies_found = []
        for ur in user_races:
            race_name = ur.race.name if ur.race else "Неизвестная раса"
            armies = db_session.query(Army).filter_by(user_race_id=ur.id).all()
            for a in armies:
                army_units = db_session.query(ArmyUnit).filter_by(army_id=a.id).all()
                units_info = []
                for unit in army_units:
                    unit_name = unit.race_unit.name if unit.race_unit else "Неизвестный"
                    level_icon = unit.unit_level.icon if unit.unit_level else ""
                    units_info.append({
                        'name': unit_name,
                        'icon': level_icon,
                        'count': unit.count
                    })
                armies_found.append({
                    'race': race_name,
                    'army_name': a.name,
                    'army_type': a.army_type,
                    'units': units_info
                })

        assert len(armies_found) == 1
        assert armies_found[0]['army_name'] == "Армия профиля"
        assert armies_found[0]['army_type'] == "mercenary"
        assert len(armies_found[0]['units']) == 1
        assert armies_found[0]['units'][0]['count'] == 5

    def test_profile_with_multiple_armies(self, db_session, test_race, test_unit_level, test_race_unit):
        """Проверка профиля с несколькими армиями"""
        game_user = GameUser(
            telegram_id=111222333,
            username=unique_name("multi_army_user"),
            balance=2000.0,
            crystals=200,
            glory=100,
            wins=10,
            losses=5
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        army1 = Army(user_race_id=user_race.id, name="Рейтинговая армия", army_type="rated")
        army2 = Army(user_race_id=user_race.id, name="Наемная армия", army_type="mercenary")
        db_session.add(army1)
        db_session.add(army2)
        db_session.flush()

        db_session.add(ArmyUnit(
            army_id=army1.id, race_unit_id=test_race_unit.id,
            unit_level_id=test_unit_level.id, count=15
        ))
        db_session.add(ArmyUnit(
            army_id=army2.id, race_unit_id=test_race_unit.id,
            unit_level_id=test_unit_level.id, count=20
        ))
        db_session.commit()

        user_races = db_session.query(UserRace).filter_by(user_id=game_user.id).all()
        total_armies = 0
        for ur in user_races:
            armies = db_session.query(Army).filter_by(user_race_id=ur.id).all()
            total_armies += len(armies)

        assert total_armies == 2

    def test_profile_with_empty_army(self, db_session, test_race):
        """Проверка профиля с пустой армией (без юнитов)"""
        game_user = GameUser(
            telegram_id=444555666,
            username=unique_name("empty_army_user"),
            balance=100.0,
            crystals=10,
            glory=5,
            wins=1,
            losses=1
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        army = Army(user_race_id=user_race.id, name="Пустая армия", army_type="rated")
        db_session.add(army)
        db_session.commit()

        army_units = db_session.query(ArmyUnit).filter_by(army_id=army.id).all()
        assert len(army_units) == 0

        user_races = db_session.query(UserRace).filter_by(user_id=game_user.id).all()
        for ur in user_races:
            armies = db_session.query(Army).filter_by(user_race_id=ur.id).all()
            for a in armies:
                units = db_session.query(ArmyUnit).filter_by(army_id=a.id).all()
                assert isinstance(units, list)


class TestArmyProfileRelationships:
    """Тесты для проверки связей в модели армий"""

    def test_user_race_game_race_relationship(self, db_session, test_race):
        """Проверка связи UserRace -> GameRace"""
        game_user = GameUser(
            telegram_id=777888999,
            username=unique_name("rel_test_user"),
            balance=100.0
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.commit()

        assert user_race.race is not None
        assert user_race.race.name == test_race.name

    def test_army_unit_race_unit_relationship(self, db_session, test_race, test_unit_level, test_race_unit):
        """Проверка связи ArmyUnit -> RaceUnit"""
        game_user = GameUser(
            telegram_id=101010101,
            username=unique_name("unit_test_user"),
            balance=100.0
        )
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        army = Army(user_race_id=user_race.id, name="Test Army", army_type="rated")
        db_session.add(army)
        db_session.flush()

        army_unit = ArmyUnit(
            army_id=army.id,
            race_unit_id=test_race_unit.id,
            unit_level_id=test_unit_level.id,
            count=7
        )
        db_session.add(army_unit)
        db_session.commit()

        assert army_unit.race_unit is not None
        assert army_unit.race_unit.name == test_race_unit.name
        assert army_unit.unit_level is not None
        assert army_unit.unit_level.icon == test_unit_level.icon


class TestArmyTypeDisplay:
    """Тесты для корректного отображения типа армии"""

    def test_rated_army_type(self, db_session, test_race):
        """Проверка типа рейтинговой армии"""
        game_user = GameUser(telegram_id=202020202, username=unique_name("rated_user"), balance=100.0)
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        army = Army(user_race_id=user_race.id, name="Rated", army_type="rated")
        db_session.add(army)
        db_session.commit()

        army_type_display = "Рейтинговая" if army.army_type == "rated" else "Наемная"
        assert army_type_display == "Рейтинговая"

    def test_mercenary_army_type(self, db_session, test_race):
        """Проверка типа наемной армии"""
        game_user = GameUser(telegram_id=303030303, username=unique_name("merc_user"), balance=100.0)
        db_session.add(game_user)
        db_session.flush()

        user_race = UserRace(user_id=game_user.id, race_id=test_race.id)
        db_session.add(user_race)
        db_session.flush()

        army = Army(user_race_id=user_race.id, name="Mercenary", army_type="mercenary")
        db_session.add(army)
        db_session.commit()

        army_type_display = "Рейтинговая" if army.army_type == "rated" else "Наемная"
        assert army_type_display == "Наемная"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
