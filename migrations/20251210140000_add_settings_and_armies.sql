-- +goose Up
-- Добавление crystals и glory в game_users
ALTER TABLE game_users ADD COLUMN IF NOT EXISTS crystals INTEGER NOT NULL DEFAULT 0;
ALTER TABLE game_users ADD COLUMN IF NOT EXISTS glory INTEGER NOT NULL DEFAULT 0;

-- Таблица игровых рас
CREATE TABLE IF NOT EXISTS game_races (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    is_free BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Таблица юнитов расы (7 уровней)
CREATE TABLE IF NOT EXISTS race_units (
    id SERIAL PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES game_races(id) ON DELETE CASCADE,
    level INTEGER NOT NULL CHECK (level >= 1 AND level <= 7),
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(10) NOT NULL DEFAULT '🎮',
    image_path VARCHAR(512),
    attack INTEGER NOT NULL DEFAULT 10,
    defense INTEGER NOT NULL DEFAULT 5,
    min_damage INTEGER NOT NULL DEFAULT 1,
    max_damage INTEGER NOT NULL DEFAULT 3,
    health INTEGER NOT NULL DEFAULT 10,
    speed INTEGER NOT NULL DEFAULT 4,
    initiative INTEGER NOT NULL DEFAULT 10,
    cost NUMERIC(10,2) NOT NULL DEFAULT 100,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_race_units_race_id ON race_units(race_id);

-- Таблица скинов уровней расы
CREATE TABLE IF NOT EXISTS race_level_skins (
    id SERIAL PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES game_races(id) ON DELETE CASCADE,
    level INTEGER NOT NULL CHECK (level >= 1 AND level <= 7),
    image_path VARCHAR(512),
    name VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_race_level_skins_race_id ON race_level_skins(race_id);

-- Таблица пользовательских рас
CREATE TABLE IF NOT EXISTS user_races (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES game_users(id) ON DELETE CASCADE,
    race_id INTEGER NOT NULL REFERENCES game_races(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_races_user_id ON user_races(user_id);
CREATE INDEX IF NOT EXISTS idx_user_races_race_id ON user_races(race_id);

-- Таблица армий (тип хранится как строка)
CREATE TABLE IF NOT EXISTS armies (
    id SERIAL PRIMARY KEY,
    user_race_id INTEGER NOT NULL REFERENCES user_races(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    army_type VARCHAR(20) NOT NULL DEFAULT 'mercenary' CHECK (army_type IN ('rated', 'mercenary')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_armies_user_race_id ON armies(user_race_id);

-- Таблица юнитов армии
CREATE TABLE IF NOT EXISTS army_units (
    id SERIAL PRIMARY KEY,
    army_id INTEGER NOT NULL REFERENCES armies(id) ON DELETE CASCADE,
    race_unit_id INTEGER NOT NULL REFERENCES race_units(id) ON DELETE CASCADE,
    skin_id INTEGER REFERENCES race_level_skins(id) ON DELETE SET NULL,
    count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_army_units_army_id ON army_units(army_id);
CREATE INDEX IF NOT EXISTS idx_army_units_race_unit_id ON army_units(race_unit_id);

-- +goose Down
DROP TABLE IF EXISTS army_units;
DROP TABLE IF EXISTS armies;
DROP TABLE IF EXISTS user_races;
DROP TABLE IF EXISTS race_level_skins;
DROP TABLE IF EXISTS race_units;
DROP TABLE IF EXISTS game_races;
ALTER TABLE game_users DROP COLUMN IF EXISTS crystals;
ALTER TABLE game_users DROP COLUMN IF EXISTS glory;
