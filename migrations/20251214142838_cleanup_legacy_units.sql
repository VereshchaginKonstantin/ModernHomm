-- +goose Up
-- +goose StatementBegin

-- Migrate battle_units from user_unit_id to army_unit_id (if column exists)
DO $$
BEGIN
    -- Check if user_unit_id column exists (if it doesn't, army_unit_id is already there)
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'battle_units' AND column_name = 'user_unit_id') THEN
        -- Drop old FK constraint
        ALTER TABLE battle_units DROP CONSTRAINT IF EXISTS battle_units_user_unit_id_fkey;

        -- Rename column
        ALTER TABLE battle_units RENAME COLUMN user_unit_id TO army_unit_id;

        -- Add new FK constraint to army_units
        ALTER TABLE battle_units ADD CONSTRAINT battle_units_army_unit_id_fkey
            FOREIGN KEY (army_unit_id) REFERENCES army_units(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Drop legacy tables (in correct order due to foreign keys)
DROP TABLE IF EXISTS unit_custom_icons;
DROP TABLE IF EXISTS user_units;
DROP TABLE IF EXISTS units;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Recreate legacy tables
CREATE TABLE IF NOT EXISTS units (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    unit_level_id INTEGER,
    min_damage INTEGER NOT NULL DEFAULT 1,
    max_damage INTEGER NOT NULL DEFAULT 1,
    health INTEGER NOT NULL DEFAULT 5,
    speed INTEGER NOT NULL DEFAULT 2,
    initiative INTEGER NOT NULL DEFAULT 5,
    range INTEGER NOT NULL DEFAULT 1,
    luck NUMERIC(5,4) NOT NULL DEFAULT 0.0,
    crit_chance NUMERIC(5,4) NOT NULL DEFAULT 0.0,
    attack INTEGER NOT NULL DEFAULT 1,
    defense INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    effective_against_unit_id INTEGER REFERENCES units(id),
    dodge_chance NUMERIC(5,4) NOT NULL DEFAULT 0.0,
    is_kamikaze INTEGER NOT NULL DEFAULT 0,
    counterattack_chance NUMERIC(5,4) NOT NULL DEFAULT 0.0,
    owner_id INTEGER REFERENCES game_users(id),
    is_flying INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_units (
    id SERIAL PRIMARY KEY,
    game_user_id INTEGER NOT NULL REFERENCES game_users(id) ON DELETE CASCADE,
    unit_type_id INTEGER NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS unit_custom_icons (
    id SERIAL PRIMARY KEY,
    unit_id INTEGER NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    icon VARCHAR(10) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(unit_id)
);

-- Revert battle_units column
ALTER TABLE battle_units DROP CONSTRAINT IF EXISTS battle_units_army_unit_id_fkey;
ALTER TABLE battle_units RENAME COLUMN army_unit_id TO user_unit_id;
ALTER TABLE battle_units ADD CONSTRAINT battle_units_user_unit_id_fkey
    FOREIGN KEY (user_unit_id) REFERENCES user_units(id) ON DELETE CASCADE;

-- +goose StatementEnd
