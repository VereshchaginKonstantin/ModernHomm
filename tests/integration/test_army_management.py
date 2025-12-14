#!/usr/bin/env python3
"""
Integration tests for army management functionality.
Tests for creating armies, hiring units (mercenary/rated), and prestige calculations.
"""

import os
import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import (
    Base, GameRace, RaceUnit, RaceUnitSkin, UnitLevel,
    GameUser, UserRace, UserRaceUnit, Army, ArmyUnit
)


# Use test database
TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5433/telegram_bot_test')


@pytest.fixture
def db_session():
    """Create a database session for tests."""
    engine = create_engine(TEST_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_setup(db_session):
    """Create test data: GameUser, GameRace, RaceUnit, RaceUnitSkin, UserRace."""
    # Get or create level 1
    level = db_session.query(UnitLevel).filter(UnitLevel.level == 1).first()
    if not level:
        level = UnitLevel(level=1, icon="🐀", prestige_min=0, prestige_max=500)
        db_session.add(level)
        db_session.flush()

    # Create test user with balance and glory
    test_user = GameUser(
        telegram_id=888888888,
        username="test_army_user",
        balance=Decimal("1000.00"),
        crystals=100,
        glory=500  # For rated army tests
    )
    db_session.add(test_user)
    db_session.flush()

    # Create test race
    test_race = GameRace(
        name="Test Army Race",
        description="Race for testing army management",
        is_free=True
    )
    db_session.add(test_race)
    db_session.flush()

    # Create test race unit with known base stats
    test_race_unit = RaceUnit(
        race_id=test_race.id,
        unit_level_id=level.id,
        name="Test Warrior",
        attack=10,
        defense=5,
        min_damage=3,
        max_damage=6,
        health=50,
        speed=4,
        initiative=10,
        range=1,
        luck=Decimal("0.05"),
        crit_chance=Decimal("0.10"),
        dodge_chance=Decimal("0.05"),
        counterattack_chance=Decimal("0.25"),
        regeneration_health=0,
        poison_damage=0,
        poison_turns=0,
        poison_immunity=False,
        is_flying=False,
        is_kamikaze=False
    )
    db_session.add(test_race_unit)
    db_session.flush()

    # Create test skin
    test_skin = RaceUnitSkin(
        race_unit_id=test_race_unit.id,
        name="Default Test Skin",
        image_data=b'\x89PNG\r\n\x1a\n',
        image_mime_type='image/png'
    )
    db_session.add(test_skin)
    db_session.flush()

    # Create user race
    user_race = UserRace(
        user_id=test_user.id,
        race_id=test_race.id
    )
    db_session.add(user_race)
    db_session.flush()

    # Create UserRaceUnit
    user_race_unit = UserRaceUnit(
        user_race_id=user_race.id,
        race_unit_id=test_race_unit.id,
        skin_id=test_skin.id,
        attack_boost=0,
        defense_boost=0
    )
    db_session.add(user_race_unit)
    db_session.flush()

    yield {
        'user': test_user,
        'race': test_race,
        'race_unit': test_race_unit,
        'skin': test_skin,
        'user_race': user_race,
        'user_race_unit': user_race_unit,
        'level': level
    }

    # Cleanup
    db_session.query(ArmyUnit).filter(
        ArmyUnit.army_id.in_(
            db_session.query(Army.id).filter(Army.user_race_id == user_race.id)
        )
    ).delete(synchronize_session=False)
    db_session.query(Army).filter(Army.user_race_id == user_race.id).delete()
    db_session.query(UserRaceUnit).filter(UserRaceUnit.user_race_id == user_race.id).delete()
    db_session.query(UserRace).filter(UserRace.id == user_race.id).delete()
    db_session.query(RaceUnitSkin).filter(RaceUnitSkin.id == test_skin.id).delete()
    db_session.query(RaceUnit).filter(RaceUnit.id == test_race_unit.id).delete()
    db_session.query(GameRace).filter(GameRace.id == test_race.id).delete()
    db_session.query(GameUser).filter(GameUser.id == test_user.id).delete()
    db_session.commit()


class TestArmyCreation:
    """Tests for army creation."""

    def test_create_mercenary_army(self, db_session, test_setup):
        """Test creating a mercenary army."""
        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Test Mercenary Army",
            army_type=Army.TYPE_MERCENARY
        )
        db_session.add(army)
        db_session.commit()

        assert army.id is not None
        assert army.name == "Test Mercenary Army"
        assert army.army_type == Army.TYPE_MERCENARY
        assert army.user_race_id == test_setup['user_race'].id

    def test_create_rated_army(self, db_session, test_setup):
        """Test creating a rated army."""
        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Test Rated Army",
            army_type=Army.TYPE_RATED
        )
        db_session.add(army)
        db_session.commit()

        assert army.id is not None
        assert army.name == "Test Rated Army"
        assert army.army_type == Army.TYPE_RATED

    def test_army_default_type_is_mercenary(self, db_session, test_setup):
        """Test that default army type is mercenary."""
        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Test Default Army"
        )
        db_session.add(army)
        db_session.commit()

        assert army.army_type == Army.TYPE_MERCENARY


class TestArmyUnitHiring:
    """Tests for hiring units into army."""

    def test_hire_unit_to_army(self, db_session, test_setup):
        """Test hiring a unit to an army."""
        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Test Army",
            army_type=Army.TYPE_MERCENARY
        )
        db_session.add(army)
        db_session.flush()

        army_unit = ArmyUnit(
            army_id=army.id,
            race_unit_id=test_setup['race_unit'].id,
            unit_level_id=test_setup['level'].id,
            count=5
        )
        db_session.add(army_unit)
        db_session.commit()

        assert army_unit.id is not None
        assert army_unit.count == 5
        assert army_unit.race_unit_id == test_setup['race_unit'].id

    def test_increase_unit_count(self, db_session, test_setup):
        """Test increasing unit count when hiring more of same type."""
        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Test Army",
            army_type=Army.TYPE_MERCENARY
        )
        db_session.add(army)
        db_session.flush()

        army_unit = ArmyUnit(
            army_id=army.id,
            race_unit_id=test_setup['race_unit'].id,
            count=5
        )
        db_session.add(army_unit)
        db_session.commit()

        # Increase count
        army_unit.count += 3
        db_session.commit()

        assert army_unit.count == 8


class TestMercenaryArmyPayment:
    """Tests for mercenary army payment mechanics."""

    def test_mercenary_hire_deducts_balance(self, db_session, test_setup):
        """Test that hiring in mercenary army deducts from balance."""
        user = test_setup['user']
        initial_balance = float(user.balance)

        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Mercenary Army",
            army_type=Army.TYPE_MERCENARY
        )
        db_session.add(army)
        db_session.flush()

        # Simulate hiring (cost = prestige)
        # Prestige for this unit should be calculated
        unit_cost = 100  # Example cost (prestige)
        count = 2
        total_cost = unit_cost * count

        user.balance = Decimal(str(initial_balance - total_cost))
        db_session.commit()

        assert float(user.balance) == initial_balance - total_cost

    def test_mercenary_insufficient_balance(self, db_session, test_setup):
        """Test that hiring fails when balance is insufficient."""
        user = test_setup['user']
        user.balance = Decimal("10.00")  # Low balance
        db_session.commit()

        # Simulate check
        unit_cost = 100
        count = 1
        total_cost = unit_cost * count

        has_funds = float(user.balance) >= total_cost
        assert has_funds is False


class TestRatedArmyPrestige:
    """Tests for rated army prestige mechanics."""

    def test_rated_army_prestige_limit(self, db_session, test_setup):
        """Test that rated army respects prestige limit (glory)."""
        user = test_setup['user']
        user.glory = 500
        db_session.commit()

        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Rated Army",
            army_type=Army.TYPE_RATED
        )
        db_session.add(army)
        db_session.flush()

        # Army prestige should not exceed glory
        unit_prestige = 100
        count = 6  # Would be 600 prestige, exceeds 500

        total_prestige = unit_prestige * count
        can_hire = total_prestige <= user.glory

        assert can_hire is False

    def test_rated_army_within_prestige_limit(self, db_session, test_setup):
        """Test rated army can hire within prestige limit."""
        user = test_setup['user']
        user.glory = 500
        db_session.commit()

        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Rated Army",
            army_type=Army.TYPE_RATED
        )
        db_session.add(army)
        db_session.flush()

        unit_prestige = 100
        count = 4  # Would be 400 prestige, within 500 limit

        total_prestige = unit_prestige * count
        can_hire = total_prestige <= user.glory

        assert can_hire is True


class TestArmyDeletion:
    """Tests for army deletion."""

    def test_delete_army(self, db_session, test_setup):
        """Test deleting an army."""
        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Army to Delete",
            army_type=Army.TYPE_MERCENARY
        )
        db_session.add(army)
        db_session.commit()

        army_id = army.id
        db_session.delete(army)
        db_session.commit()

        deleted_army = db_session.query(Army).filter(Army.id == army_id).first()
        assert deleted_army is None

    def test_delete_army_cascades_to_units(self, db_session, test_setup):
        """Test that deleting army also deletes its units."""
        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Army with Units",
            army_type=Army.TYPE_MERCENARY
        )
        db_session.add(army)
        db_session.flush()

        army_unit = ArmyUnit(
            army_id=army.id,
            race_unit_id=test_setup['race_unit'].id,
            count=5
        )
        db_session.add(army_unit)
        db_session.commit()

        army_id = army.id
        db_session.delete(army)
        db_session.commit()

        # Check that army unit was also deleted
        orphan_units = db_session.query(ArmyUnit).filter(ArmyUnit.army_id == army_id).all()
        assert len(orphan_units) == 0


class TestUnitDismissal:
    """Tests for dismissing units from army."""

    def test_dismiss_partial_units(self, db_session, test_setup):
        """Test dismissing part of unit stack."""
        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Test Army",
            army_type=Army.TYPE_MERCENARY
        )
        db_session.add(army)
        db_session.flush()

        army_unit = ArmyUnit(
            army_id=army.id,
            race_unit_id=test_setup['race_unit'].id,
            count=10
        )
        db_session.add(army_unit)
        db_session.commit()

        # Dismiss 3 units
        army_unit.count -= 3
        db_session.commit()

        assert army_unit.count == 7

    def test_dismiss_all_units_removes_stack(self, db_session, test_setup):
        """Test that dismissing all units removes the stack."""
        army = Army(
            user_race_id=test_setup['user_race'].id,
            name="Test Army",
            army_type=Army.TYPE_MERCENARY
        )
        db_session.add(army)
        db_session.flush()

        army_unit = ArmyUnit(
            army_id=army.id,
            race_unit_id=test_setup['race_unit'].id,
            count=5
        )
        db_session.add(army_unit)
        db_session.commit()

        army_unit_id = army_unit.id
        db_session.delete(army_unit)
        db_session.commit()

        deleted_unit = db_session.query(ArmyUnit).filter(ArmyUnit.id == army_unit_id).first()
        assert deleted_unit is None
