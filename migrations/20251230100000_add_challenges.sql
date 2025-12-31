-- +goose Up
-- +goose StatementBegin

-- Enum для сложности AI
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ai_difficulty') THEN
        CREATE TYPE ai_difficulty AS ENUM ('easy', 'normal', 'hard', 'nightmare');
    END IF;
END
$$;

-- Таблица челленджей
CREATE TABLE IF NOT EXISTS challenges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    reward_gold INTEGER NOT NULL DEFAULT 0,
    reward_gems INTEGER NOT NULL DEFAULT 0,
    ai_difficulty ai_difficulty NOT NULL DEFAULT 'normal',
    sprite_data BYTEA,
    sprite_mime_type VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT positive_reward_gold CHECK (reward_gold >= 0),
    CONSTRAINT positive_reward_gems CHECK (reward_gems >= 0)
);

-- Таблица юнитов челленджа
CREATE TABLE IF NOT EXISTS challenge_units (
    id SERIAL PRIMARY KEY,
    challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    race_unit_id INTEGER NOT NULL REFERENCES race_units(id) ON DELETE CASCADE,
    count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT positive_unit_count CHECK (count > 0)
);

CREATE INDEX IF NOT EXISTS idx_challenge_units_challenge_id ON challenge_units(challenge_id);
CREATE INDEX IF NOT EXISTS idx_challenge_units_race_unit_id ON challenge_units(race_unit_id);

-- Таблица прохождений челленджей
CREATE TABLE IF NOT EXISTS challenge_completions (
    id SERIAL PRIMARY KEY,
    challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES game_users(id) ON DELETE CASCADE,
    game_id INTEGER REFERENCES games(id) ON DELETE SET NULL,
    is_victory BOOLEAN NOT NULL,
    reward_gold_earned INTEGER NOT NULL DEFAULT 0,
    reward_gems_earned INTEGER NOT NULL DEFAULT 0,
    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_challenge_completions_challenge_id ON challenge_completions(challenge_id);
CREATE INDEX IF NOT EXISTS idx_challenge_completions_user_id ON challenge_completions(user_id);

-- Добавляем поля для челленджа в таблицу games
ALTER TABLE games ADD COLUMN IF NOT EXISTS is_challenge BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE games ADD COLUMN IF NOT EXISTS challenge_id INTEGER REFERENCES challenges(id) ON DELETE SET NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS ai_player_id INTEGER REFERENCES game_users(id);

CREATE INDEX IF NOT EXISTS idx_games_challenge_id ON games(challenge_id);
CREATE INDEX IF NOT EXISTS idx_games_is_challenge ON games(is_challenge);

-- Модифицируем battle_units для поддержки AI юнитов
-- Делаем army_unit_id nullable и добавляем прямую ссылку на race_unit
ALTER TABLE battle_units ALTER COLUMN army_unit_id DROP NOT NULL;
ALTER TABLE battle_units ADD COLUMN IF NOT EXISTS race_unit_id INTEGER REFERENCES race_units(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_battle_units_race_unit_id ON battle_units(race_unit_id);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Удаляем модификации battle_units
DROP INDEX IF EXISTS idx_battle_units_race_unit_id;
ALTER TABLE battle_units DROP COLUMN IF EXISTS race_unit_id;
-- Не восстанавливаем NOT NULL для army_unit_id чтобы не потерять данные

-- Удаляем индексы и колонки из games
DROP INDEX IF EXISTS idx_games_is_challenge;
DROP INDEX IF EXISTS idx_games_challenge_id;
ALTER TABLE games DROP COLUMN IF EXISTS ai_player_id;
ALTER TABLE games DROP COLUMN IF EXISTS challenge_id;
ALTER TABLE games DROP COLUMN IF EXISTS is_challenge;

-- Удаляем таблицы
DROP TABLE IF EXISTS challenge_completions;
DROP TABLE IF EXISTS challenge_units;
DROP TABLE IF EXISTS challenges;

-- Удаляем enum
DROP TYPE IF EXISTS ai_difficulty;

-- +goose StatementEnd
