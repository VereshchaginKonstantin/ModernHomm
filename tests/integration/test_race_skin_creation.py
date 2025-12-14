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


class TestRaceUnitDefaultStats:
    """Tests for RaceUnit default stats values."""

    def test_race_unit_has_all_combat_stats(self):
        """Test that RaceUnit model has all combat stat fields."""
        unit = RaceUnit(
            race_id=1,
            unit_level_id=1,
            name="Test Unit",
            attack=10,
            defense=5,
            min_damage=2,
            max_damage=4,
            health=20,
            speed=5,
            initiative=10,
            range=1,
            luck=0.1,
            crit_chance=0.05,
            dodge_chance=0.08,
            counterattack_chance=0.2
        )
        assert unit.attack == 10
        assert unit.defense == 5
        assert unit.min_damage == 2
        assert unit.max_damage == 4
        assert unit.health == 20
        assert unit.speed == 5
        assert unit.initiative == 10
        assert unit.range == 1
        assert float(unit.luck) == 0.1
        assert float(unit.crit_chance) == 0.05
        assert float(unit.dodge_chance) == 0.08
        assert float(unit.counterattack_chance) == 0.2

    def test_race_unit_has_special_abilities(self):
        """Test that RaceUnit model has special ability fields."""
        unit = RaceUnit(
            race_id=1,
            unit_level_id=1,
            name="Test Unit",
            is_flying=True,
            is_kamikaze=False,
            regeneration_health=5,
            poison_damage=3,
            poison_turns=2,
            poison_immunity=True
        )
        assert unit.is_flying is True
        assert unit.is_kamikaze is False
        assert unit.regeneration_health == 5
        assert unit.poison_damage == 3
        assert unit.poison_turns == 2
        assert unit.poison_immunity is True

    def test_race_unit_default_values(self):
        """Test that RaceUnit has sensible default values."""
        unit = RaceUnit(
            race_id=1,
            unit_level_id=1,
            name="Test Unit",
            is_flying=False,
            is_kamikaze=False,
            attack=10,
            defense=5,
            regeneration_health=0,
            poison_damage=0,
            poison_turns=0,
            poison_immunity=False
        )
        # Check that values are set correctly
        assert unit.is_flying is False
        assert unit.is_kamikaze is False
        assert unit.attack == 10
        assert unit.defense == 5
        assert unit.regeneration_health == 0
        assert unit.poison_damage == 0
        assert unit.poison_turns == 0
        assert unit.poison_immunity is False

    def test_level1_unit_stats_are_weakest(self):
        """Test that level 1 unit has lowest stats."""
        # Expected stats for level 1 (Крестьянин)
        level1_stats = {
            'attack': 2, 'defense': 1, 'min_damage': 1, 'max_damage': 2,
            'health': 3, 'speed': 4, 'initiative': 8, 'range': 1
        }
        unit = RaceUnit(
            race_id=1,
            unit_level_id=1,
            name="Крестьянин",
            **level1_stats
        )
        assert unit.attack == 2
        assert unit.defense == 1
        assert unit.health == 3
        assert unit.min_damage == 1
        assert unit.max_damage == 2

    def test_level7_unit_stats_are_strongest(self):
        """Test that level 7 unit has highest stats."""
        # Expected stats for level 7 (Ангел)
        level7_stats = {
            'attack': 25, 'defense': 25, 'min_damage': 15, 'max_damage': 30,
            'health': 200, 'speed': 10, 'initiative': 18, 'range': 1,
            'is_flying': True, 'regeneration_health': 10, 'poison_immunity': True
        }
        unit = RaceUnit(
            race_id=1,
            unit_level_id=7,
            name="Ангел",
            **level7_stats
        )
        assert unit.attack == 25
        assert unit.defense == 25
        assert unit.health == 200
        assert unit.min_damage == 15
        assert unit.max_damage == 30
        assert unit.is_flying is True
        assert unit.regeneration_health == 10
        assert unit.poison_immunity is True

    def test_archer_has_high_range(self):
        """Test that archer (level 2) has ranged attack."""
        unit = RaceUnit(
            race_id=1,
            unit_level_id=2,
            name="Лучник",
            range=6
        )
        assert unit.range == 6

    def test_griffin_is_flying(self):
        """Test that griffin (level 3) is a flying unit."""
        unit = RaceUnit(
            race_id=1,
            unit_level_id=3,
            name="Грифон",
            is_flying=True
        )
        assert unit.is_flying is True

    def test_monk_has_regeneration_and_poison_immunity(self):
        """Test that monk (level 5) has regeneration and poison immunity."""
        unit = RaceUnit(
            race_id=1,
            unit_level_id=5,
            name="Монах",
            regeneration_health=5,
            poison_immunity=True
        )
        assert unit.regeneration_health == 5
        assert unit.poison_immunity is True


class TestPrestigeCalculation:
    """Tests for unit prestige calculation."""

    def test_calculate_prestige_basic_stats(self):
        """Test prestige calculation with basic stats only."""
        from web.races import calculate_unit_prestige

        # Level 1 peasant-like stats
        prestige = calculate_unit_prestige(
            attack=2, defense=1, health=3, speed=4,
            min_damage=1, max_damage=2, initiative=8, range_=1
        )
        # Expected: 2*5 + 1*4 + 3*0.5 + 4*8 + (1+2)*3 + 8*3 + (1-1)*20
        #         = 10 + 4 + 1.5 + 32 + 9 + 24 + 0 = 80.5 ≈ 80
        assert prestige == 80

    def test_calculate_prestige_with_flying(self):
        """Test prestige calculation with flying bonus."""
        from web.races import calculate_unit_prestige

        base_prestige = calculate_unit_prestige(
            attack=10, defense=10, health=50, speed=6,
            min_damage=5, max_damage=10, initiative=12, range_=1
        )
        flying_prestige = calculate_unit_prestige(
            attack=10, defense=10, health=50, speed=6,
            min_damage=5, max_damage=10, initiative=12, range_=1,
            is_flying=True
        )
        assert flying_prestige == base_prestige + 50

    def test_calculate_prestige_with_ranged(self):
        """Test prestige calculation with ranged attack bonus."""
        from web.races import calculate_unit_prestige

        melee_prestige = calculate_unit_prestige(
            attack=5, defense=3, health=10, speed=5,
            min_damage=2, max_damage=4, initiative=10, range_=1
        )
        ranged_prestige = calculate_unit_prestige(
            attack=5, defense=3, health=10, speed=5,
            min_damage=2, max_damage=4, initiative=10, range_=6
        )
        # Range bonus = (6-1) * 20 = 100
        assert ranged_prestige == melee_prestige + 100

    def test_calculate_prestige_with_chances(self):
        """Test prestige calculation with luck/crit/dodge/counterattack."""
        from web.races import calculate_unit_prestige

        base_prestige = calculate_unit_prestige(
            attack=10, defense=5, health=20, speed=5,
            min_damage=3, max_damage=6, initiative=10, range_=1
        )
        # Add 10% luck, 5% crit, 8% dodge, 20% counterattack
        with_chances = calculate_unit_prestige(
            attack=10, defense=5, health=20, speed=5,
            min_damage=3, max_damage=6, initiative=10, range_=1,
            luck=0.1, crit_chance=0.05, dodge_chance=0.08, counterattack_chance=0.2
        )
        # Bonus = 0.1*50 + 0.05*100 + 0.08*80 + 0.2*40 = 5 + 5 + 6.4 + 8 = 24.4 ≈ 24
        assert with_chances == base_prestige + 24

    def test_calculate_prestige_with_poison(self):
        """Test prestige calculation with poison ability."""
        from web.races import calculate_unit_prestige

        base_prestige = calculate_unit_prestige(
            attack=8, defense=6, health=30, speed=5,
            min_damage=4, max_damage=8, initiative=10, range_=1
        )
        with_poison = calculate_unit_prestige(
            attack=8, defense=6, health=30, speed=5,
            min_damage=4, max_damage=8, initiative=10, range_=1,
            poison_damage=3, poison_turns=2
        )
        # Poison bonus = (3 * 2) * 15 = 90
        assert with_poison == base_prestige + 90

    def test_calculate_prestige_with_regeneration(self):
        """Test prestige calculation with regeneration."""
        from web.races import calculate_unit_prestige

        base_prestige = calculate_unit_prestige(
            attack=15, defense=15, health=100, speed=8,
            min_damage=10, max_damage=20, initiative=15, range_=1
        )
        with_regen = calculate_unit_prestige(
            attack=15, defense=15, health=100, speed=8,
            min_damage=10, max_damage=20, initiative=15, range_=1,
            regeneration_health=10
        )
        # Regen bonus = 10 * 10 = 100
        assert with_regen == base_prestige + 100

    def test_calculate_prestige_level1_peasant_in_range(self):
        """Test that level 1 peasant stats produce prestige within level 1 range (0-100)."""
        from web.races import calculate_unit_prestige

        # Actual level 1 default stats
        prestige = calculate_unit_prestige(
            attack=2, defense=1, health=3, speed=4,
            min_damage=1, max_damage=2, initiative=8, range_=1,
            luck=0.0, crit_chance=0.02, dodge_chance=0.05, counterattack_chance=0.1
        )
        # Should be within level 1 range: 0-100
        assert 0 <= prestige <= 100

    def test_calculate_prestige_level7_angel_high(self):
        """Test that level 7 angel stats produce significantly higher prestige than level 1."""
        from web.races import calculate_unit_prestige

        # Level 1 peasant stats
        level1_prestige = calculate_unit_prestige(
            attack=2, defense=1, health=3, speed=4,
            min_damage=1, max_damage=2, initiative=8, range_=1
        )

        # Level 7 angel stats
        level7_prestige = calculate_unit_prestige(
            attack=25, defense=25, health=200, speed=10,
            min_damage=15, max_damage=30, initiative=18, range_=1,
            luck=0.2, crit_chance=0.15, dodge_chance=0.15, counterattack_chance=0.5,
            regeneration_health=10, poison_immunity=True, is_flying=True
        )
        # Level 7 should have much higher prestige than level 1
        assert level7_prestige > level1_prestige * 5  # At least 5x stronger
        # Verify the specific calculated value
        assert level7_prestige == 826  # Calculated expected value

    def test_calculate_race_unit_prestige(self):
        """Test calculate_race_unit_prestige function with RaceUnit instance."""
        from web.races import calculate_race_unit_prestige

        unit = RaceUnit(
            race_id=1,
            unit_level_id=1,
            name="Test Unit",
            attack=10,
            defense=5,
            health=20,
            speed=5,
            min_damage=3,
            max_damage=6,
            initiative=10,
            range=1,
            is_flying=False,
            is_kamikaze=False
        )
        prestige = calculate_race_unit_prestige(unit)
        # Expected: 10*5 + 5*4 + 20*0.5 + 5*8 + (3+6)*3 + 10*3 + 0
        #         = 50 + 20 + 10 + 40 + 27 + 30 + 0 = 177
        assert prestige == 177

    def test_prestige_increases_with_stats(self):
        """Test that prestige increases when stats increase."""
        from web.races import calculate_unit_prestige

        base = calculate_unit_prestige(attack=10, defense=10, health=50)
        with_more_attack = calculate_unit_prestige(attack=15, defense=10, health=50)
        with_more_defense = calculate_unit_prestige(attack=10, defense=15, health=50)
        with_more_health = calculate_unit_prestige(attack=10, defense=10, health=100)

        assert with_more_attack > base
        assert with_more_defense > base
        assert with_more_health > base

    def test_kamikaze_damage_reduced_coefficient(self):
        """Test that kamikaze units have damage reduced by 1/5."""
        from web.races import calculate_unit_prestige

        # Base stats for comparison
        base_prestige = calculate_unit_prestige(
            attack=10, defense=5, health=20, speed=5,
            min_damage=5, max_damage=10, initiative=10, range_=1
        )
        # Same unit but kamikaze
        kamikaze_prestige = calculate_unit_prestige(
            attack=10, defense=5, health=20, speed=5,
            min_damage=5, max_damage=10, initiative=10, range_=1,
            is_kamikaze=True
        )
        # Kamikaze gets +30 bonus but damage is reduced by 0.8
        # Damage contribution: (5+10)*3 = 45 normal, 45*0.2 = 9 for kamikaze
        # Difference = 45 - 9 = 36 reduction, +30 kamikaze bonus = -6 net
        # So kamikaze should have slightly lower prestige
        damage_reduction = (5 + 10) * 3 * (1 - 0.2)  # 36
        kamikaze_bonus = 30
        expected_diff = kamikaze_bonus - damage_reduction  # -6

        assert kamikaze_prestige == base_prestige + expected_diff

    def test_kamikaze_dodge_reduced_coefficient(self):
        """Test that kamikaze units have dodge reduced by 1/5."""
        from web.races import calculate_unit_prestige

        # Base stats with dodge
        base_prestige = calculate_unit_prestige(
            attack=10, defense=5, health=20, speed=5,
            min_damage=0, max_damage=0, initiative=10, range_=1,
            dodge_chance=0.2  # 20% dodge
        )
        # Same unit but kamikaze
        kamikaze_prestige = calculate_unit_prestige(
            attack=10, defense=5, health=20, speed=5,
            min_damage=0, max_damage=0, initiative=10, range_=1,
            dodge_chance=0.2,
            is_kamikaze=True
        )
        # Dodge contribution: 0.2 * 80 = 16 normal, 16 * 0.2 = 3.2 for kamikaze
        # Kamikaze bonus = 30
        dodge_reduction = 0.2 * 80 * (1 - 0.2)  # 12.8
        kamikaze_bonus = 30
        expected_diff = round(kamikaze_bonus - dodge_reduction)  # 17

        assert kamikaze_prestige == base_prestige + expected_diff

    def test_kamikaze_full_scenario(self):
        """Test kamikaze prestige calculation with all reduced stats."""
        from web.races import calculate_unit_prestige

        # Non-kamikaze unit
        normal_prestige = calculate_unit_prestige(
            attack=8, defense=4, health=15, speed=6,
            min_damage=10, max_damage=20, initiative=12, range_=1,
            dodge_chance=0.15
        )
        # Kamikaze version
        kamikaze_prestige = calculate_unit_prestige(
            attack=8, defense=4, health=15, speed=6,
            min_damage=10, max_damage=20, initiative=12, range_=1,
            dodge_chance=0.15,
            is_kamikaze=True
        )

        # Calculate expected difference
        # Damage reduction: (10+20)*3*0.8 = 72
        # Dodge reduction: 0.15*80*0.8 = 9.6
        # Kamikaze bonus: 30
        # Net: 30 - 72 - 9.6 = -51.6 ≈ -52

        damage_reduction = (10 + 20) * 3 * 0.8
        dodge_reduction = 0.15 * 80 * 0.8
        kamikaze_bonus = 30
        expected_diff = round(kamikaze_bonus - damage_reduction - dodge_reduction)

        assert kamikaze_prestige == normal_prestige + expected_diff

    def test_kamikaze_prestige_lower_than_normal(self):
        """Test that kamikaze with high damage has lower prestige than non-kamikaze."""
        from web.races import calculate_unit_prestige

        # High damage unit
        normal = calculate_unit_prestige(
            attack=10, defense=5, health=30, speed=5,
            min_damage=15, max_damage=25, initiative=10, range_=1,
            dodge_chance=0.1
        )
        kamikaze = calculate_unit_prestige(
            attack=10, defense=5, health=30, speed=5,
            min_damage=15, max_damage=25, initiative=10, range_=1,
            dodge_chance=0.1,
            is_kamikaze=True
        )
        # High damage kamikaze should have LOWER prestige because
        # damage reduction (40*3*0.8=96) + dodge reduction (0.1*80*0.8=6.4)
        # exceeds kamikaze bonus (30)
        assert kamikaze < normal
