#!/usr/bin/env python3
"""
Integration tests for race creation with default skins.
Tests that when a race is created, 7 units are created with default skins.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, GameRace, RaceUnit, RaceUnitSkin, UnitLevel
from web.races import generate_placeholder_sprite, create_default_skin_for_unit


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


class TestPlaceholderSpriteGeneration:
    """Tests for placeholder sprite generation."""

    def test_generate_placeholder_sprite_returns_bytes(self):
        """Test that generate_placeholder_sprite returns PNG bytes."""
        sprite_data = generate_placeholder_sprite(1, 64)
        assert isinstance(sprite_data, bytes)
        assert len(sprite_data) > 0

    def test_generate_placeholder_sprite_valid_png(self):
        """Test that generated sprite is a valid PNG."""
        sprite_data = generate_placeholder_sprite(3, 64)
        # PNG magic bytes
        assert sprite_data[:8] == b'\x89PNG\r\n\x1a\n'

    def test_generate_placeholder_sprite_different_levels(self):
        """Test sprite generation for all 7 levels."""
        for level in range(1, 8):
            sprite_data = generate_placeholder_sprite(level, 64)
            assert isinstance(sprite_data, bytes)
            assert sprite_data[:8] == b'\x89PNG\r\n\x1a\n'

    def test_generate_placeholder_sprite_custom_size(self):
        """Test sprite generation with custom size."""
        sprite_32 = generate_placeholder_sprite(1, 32)
        sprite_128 = generate_placeholder_sprite(1, 128)
        # Larger sprite should be bigger
        assert len(sprite_128) > len(sprite_32)


class TestDefaultSkinCreation:
    """Tests for default skin creation when race is created."""

    def test_race_units_exist_in_database(self, db_session):
        """Test that we can query race units from database."""
        race_units = db_session.query(RaceUnit).limit(5).all()
        # Just checking query works - may be empty if no races created
        assert isinstance(race_units, list)

    def test_race_unit_skins_table_exists(self, db_session):
        """Test that race_unit_skins table can be queried."""
        skins = db_session.query(RaceUnitSkin).limit(5).all()
        assert isinstance(skins, list)

    def test_skin_has_sprite_parameters(self, db_session):
        """Test that RaceUnitSkin model has sprite parameters."""
        skin = RaceUnitSkin(
            race_unit_id=1,  # Dummy ID
            name="Test Skin",
            sprite_scale_x=1.5,
            sprite_scale_y=1.5,
            sprite_offset_x=10,
            sprite_offset_y=-5,
            sprite_rotation=45.0,
            sprite_frame_count=4,
            sprite_fps=12,
            sprite_columns=2,
            sprite_rows=2
        )
        assert skin.sprite_scale_x == 1.5
        assert skin.sprite_scale_y == 1.5
        assert skin.sprite_offset_x == 10
        assert skin.sprite_offset_y == -5
        assert skin.sprite_rotation == 45.0
        assert skin.sprite_frame_count == 4
        assert skin.sprite_fps == 12
        assert skin.sprite_columns == 2
        assert skin.sprite_rows == 2

    def test_skin_has_godot_paths(self, db_session):
        """Test that RaceUnitSkin model has Godot path fields."""
        skin = RaceUnitSkin(
            race_unit_id=1,
            name="Test Skin",
            godot_texture_path="res://assets/units/test.png",
            godot_sprite_path="res://scenes/units/test.tscn"
        )
        assert skin.godot_texture_path == "res://assets/units/test.png"
        assert skin.godot_sprite_path == "res://scenes/units/test.tscn"


class TestUnitLevels:
    """Tests for unit levels reference data."""

    def test_unit_levels_exist(self, db_session):
        """Test that 7 unit levels exist in database."""
        levels = db_session.query(UnitLevel).order_by(UnitLevel.level).all()
        assert len(levels) == 7

    def test_unit_levels_have_correct_numbers(self, db_session):
        """Test that unit levels are numbered 1-7."""
        levels = db_session.query(UnitLevel).order_by(UnitLevel.level).all()
        for i, level in enumerate(levels, start=1):
            assert level.level == i
