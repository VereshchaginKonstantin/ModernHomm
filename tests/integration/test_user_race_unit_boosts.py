#!/usr/bin/env python3
"""
Integration tests for UserRaceUnit boost functionality.
Tests that UserRaceUnit properly stores boosts and calculates final stats.
"""

import os
import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import (
    Base, GameRace, RaceUnit, RaceUnitSkin, UnitLevel,
    GameUser, UserRace, UserRaceUnit
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
    """Create test data: GameUser, GameRace, RaceUnit, RaceUnitSkin."""
    # Get or create level 1
    level = db_session.query(UnitLevel).filter(UnitLevel.level == 1).first()
    if not level:
        level = UnitLevel(level=1, icon="🐀", prestige_min=0, prestige_max=500)
        db_session.add(level)
        db_session.flush()

    # Create test user
    test_user = GameUser(
        telegram_id=999999999,
        username="test_boost_user",
        balance=1000.0,
        crystals=100
    )
    db_session.add(test_user)
    db_session.flush()

    # Create test race
    test_race = GameRace(
        name="Test Boost Race",
        description="Race for testing boosts",
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

    yield {
        'user': test_user,
        'race': test_race,
        'race_unit': test_race_unit,
        'skin': test_skin,
        'user_race': user_race,
        'level': level
    }

    # Cleanup
    db_session.query(UserRaceUnit).filter(UserRaceUnit.user_race_id == user_race.id).delete()
    db_session.query(UserRace).filter(UserRace.id == user_race.id).delete()
    db_session.query(RaceUnitSkin).filter(RaceUnitSkin.id == test_skin.id).delete()
    db_session.query(RaceUnit).filter(RaceUnit.id == test_race_unit.id).delete()
    db_session.query(GameRace).filter(GameRace.id == test_race.id).delete()
    db_session.query(GameUser).filter(GameUser.id == test_user.id).delete()
    db_session.commit()


class TestUserRaceUnitBoostCreation:
    """Tests for UserRaceUnit creation with default boost values."""

    def test_create_user_race_unit_with_zero_boosts(self, db_session, test_setup):
        """Test that UserRaceUnit is created with zero boosts by default."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id
        )
        db_session.add(user_race_unit)
        db_session.commit()

        # Verify all boosts are zero
        assert user_race_unit.attack_boost == 0
        assert user_race_unit.defense_boost == 0
        assert user_race_unit.min_damage_boost == 0
        assert user_race_unit.max_damage_boost == 0
        assert user_race_unit.health_boost == 0
        assert user_race_unit.speed_boost == 0
        assert user_race_unit.initiative_boost == 0
        assert user_race_unit.range_boost == 0
        assert float(user_race_unit.luck_boost) == 0.0
        assert float(user_race_unit.crit_chance_boost) == 0.0
        assert float(user_race_unit.dodge_chance_boost) == 0.0
        assert float(user_race_unit.counterattack_chance_boost) == 0.0

    def test_create_user_race_unit_with_positive_boosts(self, db_session, test_setup):
        """Test that UserRaceUnit can be created with positive boosts."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id,
            attack_boost=5,
            defense_boost=3,
            health_boost=20,
            speed_boost=2
        )
        db_session.add(user_race_unit)
        db_session.commit()

        assert user_race_unit.attack_boost == 5
        assert user_race_unit.defense_boost == 3
        assert user_race_unit.health_boost == 20
        assert user_race_unit.speed_boost == 2

    def test_create_user_race_unit_with_negative_boosts(self, db_session, test_setup):
        """Test that UserRaceUnit can be created with negative boosts."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id,
            attack_boost=-2,
            defense_boost=-1,
            health_boost=-10
        )
        db_session.add(user_race_unit)
        db_session.commit()

        assert user_race_unit.attack_boost == -2
        assert user_race_unit.defense_boost == -1
        assert user_race_unit.health_boost == -10


class TestUserRaceUnitFinalStatsCalculation:
    """Tests for UserRaceUnit computed final stats (base + boost)."""

    def test_final_attack_with_zero_boost(self, db_session, test_setup):
        """Test final attack equals base attack when boost is zero."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id,
            attack_boost=0
        )
        db_session.add(user_race_unit)
        db_session.commit()

        # Base attack is 10
        assert user_race_unit.attack == 10

    def test_final_attack_with_positive_boost(self, db_session, test_setup):
        """Test final attack = base + positive boost."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id,
            attack_boost=5
        )
        db_session.add(user_race_unit)
        db_session.commit()

        # Base attack (10) + boost (5) = 15
        assert user_race_unit.attack == 15

    def test_final_attack_with_negative_boost(self, db_session, test_setup):
        """Test final attack = base + negative boost."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id,
            attack_boost=-3
        )
        db_session.add(user_race_unit)
        db_session.commit()

        # Base attack (10) + boost (-3) = 7
        assert user_race_unit.attack == 7

    def test_all_final_stats_calculation(self, db_session, test_setup):
        """Test that all final stats are correctly calculated."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id,
            attack_boost=5,       # 10 + 5 = 15
            defense_boost=3,      # 5 + 3 = 8
            min_damage_boost=2,   # 3 + 2 = 5
            max_damage_boost=4,   # 6 + 4 = 10
            health_boost=25,      # 50 + 25 = 75
            speed_boost=2,        # 4 + 2 = 6
            initiative_boost=5,   # 10 + 5 = 15
            range_boost=1         # 1 + 1 = 2
        )
        db_session.add(user_race_unit)
        db_session.commit()

        # Verify computed properties
        assert user_race_unit.attack == 15
        assert user_race_unit.defense == 8
        assert user_race_unit.min_damage == 5
        assert user_race_unit.max_damage == 10
        assert user_race_unit.health == 75
        assert user_race_unit.speed == 6
        assert user_race_unit.initiative == 15
        assert user_race_unit.range == 2

    def test_final_luck_calculation(self, db_session, test_setup):
        """Test final luck stat with decimal boost."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id,
            luck_boost=Decimal("0.03")
        )
        db_session.add(user_race_unit)
        db_session.commit()

        # Base luck (0.05) + boost (0.03) = 0.08
        assert abs(user_race_unit.luck - 0.08) < 0.0001

    def test_final_crit_chance_calculation(self, db_session, test_setup):
        """Test final crit_chance stat with decimal boost."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id,
            crit_chance_boost=Decimal("0.05")
        )
        db_session.add(user_race_unit)
        db_session.commit()

        # Base crit_chance (0.10) + boost (0.05) = 0.15
        assert abs(user_race_unit.crit_chance - 0.15) < 0.0001


class TestUserRaceUnitBoostUpdate:
    """Tests for updating UserRaceUnit boosts."""

    def test_update_boost_values(self, db_session, test_setup):
        """Test that boost values can be updated."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id,
            attack_boost=5
        )
        db_session.add(user_race_unit)
        db_session.commit()

        # Verify initial
        assert user_race_unit.attack == 15  # 10 + 5

        # Update boost
        user_race_unit.attack_boost = 10
        db_session.commit()

        # Verify updated
        assert user_race_unit.attack == 20  # 10 + 10

    def test_update_multiple_boosts(self, db_session, test_setup):
        """Test updating multiple boosts at once."""
        user_race_unit = UserRaceUnit(
            user_race_id=test_setup['user_race'].id,
            race_unit_id=test_setup['race_unit'].id,
            skin_id=test_setup['skin'].id
        )
        db_session.add(user_race_unit)
        db_session.commit()

        # Update multiple boosts
        user_race_unit.attack_boost = 10
        user_race_unit.defense_boost = 5
        user_race_unit.health_boost = 50
        user_race_unit.range_boost = 3
        db_session.commit()

        # Verify all updates
        assert user_race_unit.attack == 20   # 10 + 10
        assert user_race_unit.defense == 10  # 5 + 5
        assert user_race_unit.health == 100  # 50 + 50
        assert user_race_unit.range == 4     # 1 + 3
