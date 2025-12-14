-- +goose Up
-- +goose StatementBegin

-- Add regeneration and poison fields to units table
ALTER TABLE units ADD COLUMN IF NOT EXISTS regeneration_health INTEGER NOT NULL DEFAULT 0;
ALTER TABLE units ADD COLUMN IF NOT EXISTS poison_damage INTEGER NOT NULL DEFAULT 0;
ALTER TABLE units ADD COLUMN IF NOT EXISTS poison_turns INTEGER NOT NULL DEFAULT 0;
ALTER TABLE units ADD COLUMN IF NOT EXISTS poison_immunity INTEGER NOT NULL DEFAULT 0;

-- Add battle characteristics to race_units table (moved from user_race_units)
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS attack INTEGER NOT NULL DEFAULT 10;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS defense INTEGER NOT NULL DEFAULT 5;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS min_damage INTEGER NOT NULL DEFAULT 1;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS max_damage INTEGER NOT NULL DEFAULT 3;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS health INTEGER NOT NULL DEFAULT 10;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS speed INTEGER NOT NULL DEFAULT 4;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS initiative INTEGER NOT NULL DEFAULT 10;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS luck NUMERIC(5, 4) NOT NULL DEFAULT 0;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS crit_chance NUMERIC(5, 4) NOT NULL DEFAULT 0;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS dodge_chance NUMERIC(5, 4) NOT NULL DEFAULT 0;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS counterattack_chance NUMERIC(5, 4) NOT NULL DEFAULT 0;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS range INTEGER NOT NULL DEFAULT 1;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS regeneration_health INTEGER NOT NULL DEFAULT 0;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS poison_damage INTEGER NOT NULL DEFAULT 0;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS poison_turns INTEGER NOT NULL DEFAULT 0;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS poison_immunity BOOLEAN NOT NULL DEFAULT FALSE;

-- Migrate existing data from user_race_units to race_units (take first user's values as base)
UPDATE race_units ru SET
    attack = COALESCE((SELECT uru.attack FROM user_race_units uru WHERE uru.race_unit_id = ru.id LIMIT 1), 10),
    defense = COALESCE((SELECT uru.defense FROM user_race_units uru WHERE uru.race_unit_id = ru.id LIMIT 1), 5),
    min_damage = COALESCE((SELECT uru.min_damage FROM user_race_units uru WHERE uru.race_unit_id = ru.id LIMIT 1), 1),
    max_damage = COALESCE((SELECT uru.max_damage FROM user_race_units uru WHERE uru.race_unit_id = ru.id LIMIT 1), 3),
    health = COALESCE((SELECT uru.health FROM user_race_units uru WHERE uru.race_unit_id = ru.id LIMIT 1), 10),
    speed = COALESCE((SELECT uru.speed FROM user_race_units uru WHERE uru.race_unit_id = ru.id LIMIT 1), 4),
    initiative = COALESCE((SELECT uru.initiative FROM user_race_units uru WHERE uru.race_unit_id = ru.id LIMIT 1), 10)
WHERE EXISTS (SELECT 1 FROM user_race_units uru WHERE uru.race_unit_id = ru.id);

-- Rename old columns in user_race_units to boost columns
ALTER TABLE user_race_units RENAME COLUMN attack TO attack_boost;
ALTER TABLE user_race_units RENAME COLUMN defense TO defense_boost;
ALTER TABLE user_race_units RENAME COLUMN min_damage TO min_damage_boost;
ALTER TABLE user_race_units RENAME COLUMN max_damage TO max_damage_boost;
ALTER TABLE user_race_units RENAME COLUMN health TO health_boost;
ALTER TABLE user_race_units RENAME COLUMN speed TO speed_boost;
ALTER TABLE user_race_units RENAME COLUMN initiative TO initiative_boost;

-- Set all boost values to 0 (since base values are now in race_units)
UPDATE user_race_units SET
    attack_boost = 0,
    defense_boost = 0,
    min_damage_boost = 0,
    max_damage_boost = 0,
    health_boost = 0,
    speed_boost = 0,
    initiative_boost = 0;

-- Add new boost columns for additional stats
ALTER TABLE user_race_units ADD COLUMN IF NOT EXISTS luck_boost NUMERIC(5, 4) NOT NULL DEFAULT 0;
ALTER TABLE user_race_units ADD COLUMN IF NOT EXISTS crit_chance_boost NUMERIC(5, 4) NOT NULL DEFAULT 0;
ALTER TABLE user_race_units ADD COLUMN IF NOT EXISTS dodge_chance_boost NUMERIC(5, 4) NOT NULL DEFAULT 0;
ALTER TABLE user_race_units ADD COLUMN IF NOT EXISTS counterattack_chance_boost NUMERIC(5, 4) NOT NULL DEFAULT 0;
ALTER TABLE user_race_units ADD COLUMN IF NOT EXISTS range_boost INTEGER NOT NULL DEFAULT 0;
ALTER TABLE user_race_units ADD COLUMN IF NOT EXISTS regeneration_health_boost INTEGER NOT NULL DEFAULT 0;
ALTER TABLE user_race_units ADD COLUMN IF NOT EXISTS poison_damage_boost INTEGER NOT NULL DEFAULT 0;
ALTER TABLE user_race_units ADD COLUMN IF NOT EXISTS poison_turns_boost INTEGER NOT NULL DEFAULT 0;

-- Add poison effect tracking to battle_units
ALTER TABLE battle_units ADD COLUMN IF NOT EXISTS poison_remaining_turns INTEGER NOT NULL DEFAULT 0;
ALTER TABLE battle_units ADD COLUMN IF NOT EXISTS poison_damage_per_turn INTEGER NOT NULL DEFAULT 0;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Remove poison effect tracking from battle_units
ALTER TABLE battle_units DROP COLUMN IF EXISTS poison_remaining_turns;
ALTER TABLE battle_units DROP COLUMN IF EXISTS poison_damage_per_turn;

-- Remove new boost columns from user_race_units
ALTER TABLE user_race_units DROP COLUMN IF EXISTS luck_boost;
ALTER TABLE user_race_units DROP COLUMN IF EXISTS crit_chance_boost;
ALTER TABLE user_race_units DROP COLUMN IF EXISTS dodge_chance_boost;
ALTER TABLE user_race_units DROP COLUMN IF EXISTS counterattack_chance_boost;
ALTER TABLE user_race_units DROP COLUMN IF EXISTS range_boost;
ALTER TABLE user_race_units DROP COLUMN IF EXISTS regeneration_health_boost;
ALTER TABLE user_race_units DROP COLUMN IF EXISTS poison_damage_boost;
ALTER TABLE user_race_units DROP COLUMN IF EXISTS poison_turns_boost;

-- Rename boost columns back to original names
ALTER TABLE user_race_units RENAME COLUMN attack_boost TO attack;
ALTER TABLE user_race_units RENAME COLUMN defense_boost TO defense;
ALTER TABLE user_race_units RENAME COLUMN min_damage_boost TO min_damage;
ALTER TABLE user_race_units RENAME COLUMN max_damage_boost TO max_damage;
ALTER TABLE user_race_units RENAME COLUMN health_boost TO health;
ALTER TABLE user_race_units RENAME COLUMN speed_boost TO speed;
ALTER TABLE user_race_units RENAME COLUMN initiative_boost TO initiative;

-- Remove battle characteristics from race_units
ALTER TABLE race_units DROP COLUMN IF EXISTS attack;
ALTER TABLE race_units DROP COLUMN IF EXISTS defense;
ALTER TABLE race_units DROP COLUMN IF EXISTS min_damage;
ALTER TABLE race_units DROP COLUMN IF EXISTS max_damage;
ALTER TABLE race_units DROP COLUMN IF EXISTS health;
ALTER TABLE race_units DROP COLUMN IF EXISTS speed;
ALTER TABLE race_units DROP COLUMN IF EXISTS initiative;
ALTER TABLE race_units DROP COLUMN IF EXISTS luck;
ALTER TABLE race_units DROP COLUMN IF EXISTS crit_chance;
ALTER TABLE race_units DROP COLUMN IF EXISTS dodge_chance;
ALTER TABLE race_units DROP COLUMN IF EXISTS counterattack_chance;
ALTER TABLE race_units DROP COLUMN IF EXISTS range;
ALTER TABLE race_units DROP COLUMN IF EXISTS regeneration_health;
ALTER TABLE race_units DROP COLUMN IF EXISTS poison_damage;
ALTER TABLE race_units DROP COLUMN IF EXISTS poison_turns;
ALTER TABLE race_units DROP COLUMN IF EXISTS poison_immunity;

-- Remove regeneration and poison fields from units table
ALTER TABLE units DROP COLUMN IF EXISTS regeneration_health;
ALTER TABLE units DROP COLUMN IF EXISTS poison_damage;
ALTER TABLE units DROP COLUMN IF EXISTS poison_turns;
ALTER TABLE units DROP COLUMN IF EXISTS poison_immunity;

-- +goose StatementEnd
