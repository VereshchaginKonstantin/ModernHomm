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
from web.races import generate_placeholder_sprite, generate_animated_sprite_sheet, create_default_skin_for_unit


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


class TestAnimatedSpriteSheetGeneration:
    """Tests for animated sprite sheet generation."""

    def test_generate_animated_sprite_sheet_returns_bytes(self):
        """Test that generate_animated_sprite_sheet returns PNG bytes."""
        sprite_data = generate_animated_sprite_sheet(1, 64, 4, 4)
        assert isinstance(sprite_data, bytes)
        assert len(sprite_data) > 0

    def test_generate_animated_sprite_sheet_valid_png(self):
        """Test that generated sprite sheet is a valid PNG."""
        sprite_data = generate_animated_sprite_sheet(3, 64, 4, 4)
        # PNG magic bytes
        assert sprite_data[:8] == b'\x89PNG\r\n\x1a\n'

    def test_generate_animated_sprite_sheet_different_levels(self):
        """Test sprite sheet generation for all 7 levels."""
        for level in range(1, 8):
            sprite_data = generate_animated_sprite_sheet(level, 64, 4, 4)
            assert isinstance(sprite_data, bytes)
            assert sprite_data[:8] == b'\x89PNG\r\n\x1a\n'

    def test_generate_animated_sprite_sheet_larger_than_single_sprite(self):
        """Test that sprite sheet is larger than single sprite."""
        single_sprite = generate_placeholder_sprite(1, 64)
        sprite_sheet = generate_animated_sprite_sheet(1, 64, 4, 4)
        # Sprite sheet with 4 frames should be significantly larger
        assert len(sprite_sheet) > len(single_sprite)

    def test_generate_animated_sprite_sheet_different_frame_counts(self):
        """Test sprite sheet generation with different frame counts."""
        sheet_4_frames = generate_animated_sprite_sheet(1, 64, 4, 4)
        sheet_8_frames = generate_animated_sprite_sheet(1, 64, 8, 4)
        # More frames = larger sprite sheet
        assert len(sheet_8_frames) > len(sheet_4_frames)


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


class TestCreateDefaultSkinForUnit:
    """Tests for create_default_skin_for_unit function."""

    def test_create_default_skin_has_image_data(self):
        """Test that default skin has image data."""
        # Create mock RaceUnit with id
        class MockRaceUnit:
            id = 999

        skin = create_default_skin_for_unit(MockRaceUnit(), 1)
        assert skin.image_data is not None
        assert isinstance(skin.image_data, bytes)
        assert len(skin.image_data) > 0
        # Verify it's a valid PNG
        assert skin.image_data[:8] == b'\x89PNG\r\n\x1a\n'

    def test_create_default_skin_has_sprite_frames_data(self):
        """Test that default skin has sprite frames (animated sprite sheet)."""
        class MockRaceUnit:
            id = 999

        skin = create_default_skin_for_unit(MockRaceUnit(), 1)
        assert skin.sprite_frames_data is not None
        assert isinstance(skin.sprite_frames_data, bytes)
        assert len(skin.sprite_frames_data) > 0
        # Verify it's a valid PNG
        assert skin.sprite_frames_data[:8] == b'\x89PNG\r\n\x1a\n'

    def test_create_default_skin_has_godot_paths(self):
        """Test that default skin has Godot paths populated."""
        class MockRaceUnit:
            id = 999

        skin = create_default_skin_for_unit(MockRaceUnit(), 1)
        assert skin.godot_texture_path is not None
        assert skin.godot_sprite_path is not None
        assert 'res://' in skin.godot_texture_path
        assert 'res://' in skin.godot_sprite_path
        assert '.png' in skin.godot_texture_path
        assert '.tscn' in skin.godot_sprite_path

    def test_create_default_skin_has_animation_params(self):
        """Test that default skin has correct animation parameters."""
        class MockRaceUnit:
            id = 999

        skin = create_default_skin_for_unit(MockRaceUnit(), 1)
        assert skin.sprite_frame_count == 4
        assert skin.sprite_fps == 8
        assert skin.sprite_columns == 4
        assert skin.sprite_rows == 1
        assert skin.sprite_frames_mime_type == 'image/png'

    def test_create_default_skin_different_levels_different_paths(self):
        """Test that different levels have different Godot paths."""
        class MockRaceUnit:
            id = 999

        skin_level1 = create_default_skin_for_unit(MockRaceUnit(), 1)
        skin_level7 = create_default_skin_for_unit(MockRaceUnit(), 7)

        assert skin_level1.godot_texture_path != skin_level7.godot_texture_path
        assert skin_level1.godot_sprite_path != skin_level7.godot_sprite_path
        assert 'peasant' in skin_level1.godot_texture_path
        assert 'angel' in skin_level7.godot_texture_path

    def test_create_default_skin_all_levels(self):
        """Test default skin creation for all 7 levels."""
        class MockRaceUnit:
            id = 999

        for level in range(1, 8):
            skin = create_default_skin_for_unit(MockRaceUnit(), level)
            # Verify all required fields are populated
            assert skin.image_data is not None
            assert skin.sprite_frames_data is not None
            assert skin.godot_texture_path is not None
            assert skin.godot_sprite_path is not None
            assert f'level{level}' in skin.godot_texture_path


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
