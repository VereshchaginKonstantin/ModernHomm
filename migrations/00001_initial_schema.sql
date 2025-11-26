-- +goose Up
-- Создание таблицы пользователей Telegram
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);

-- Создание таблицы сообщений
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    message_text TEXT NOT NULL,
    message_date TIMESTAMP NOT NULL DEFAULT NOW(),
    username VARCHAR(255)
);

CREATE INDEX idx_messages_telegram_user_id ON messages(telegram_user_id);

-- Создание таблицы игровых пользователей
CREATE TABLE game_users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    balance NUMERIC(12, 2) NOT NULL DEFAULT 1000,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_game_users_telegram_id ON game_users(telegram_id);

-- Создание таблицы типов юнитов
CREATE TABLE units (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    price NUMERIC(12, 2) NOT NULL,
    damage INTEGER NOT NULL,
    defense INTEGER NOT NULL DEFAULT 0,
    range INTEGER NOT NULL,
    health INTEGER NOT NULL,
    speed INTEGER NOT NULL DEFAULT 1,
    luck NUMERIC(5, 4) NOT NULL DEFAULT 0,
    crit_chance NUMERIC(5, 4) NOT NULL DEFAULT 0
);

-- Создание таблицы юнитов пользователя
CREATE TABLE user_units (
    id SERIAL PRIMARY KEY,
    game_user_id INTEGER NOT NULL REFERENCES game_users(id) ON DELETE CASCADE,
    unit_type_id INTEGER NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_user_units_game_user_id ON user_units(game_user_id);
CREATE INDEX idx_user_units_unit_type_id ON user_units(unit_type_id);

-- Создание таблицы игровых полей
CREATE TABLE fields (
    id SERIAL PRIMARY KEY,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL UNIQUE,
    CONSTRAINT positive_dimensions CHECK (width > 0 AND height > 0)
);

-- Создание типа для статуса игры
CREATE TYPE game_status AS ENUM ('waiting', 'in_progress', 'completed');

-- Создание таблицы игр
CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    player1_id INTEGER NOT NULL REFERENCES game_users(id) ON DELETE CASCADE,
    player2_id INTEGER NOT NULL REFERENCES game_users(id) ON DELETE CASCADE,
    field_id INTEGER NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    status game_status NOT NULL DEFAULT 'waiting',
    current_player_id INTEGER REFERENCES game_users(id),
    winner_id INTEGER REFERENCES game_users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_move_at TIMESTAMP
);

CREATE INDEX idx_games_player1_id ON games(player1_id);
CREATE INDEX idx_games_player2_id ON games(player2_id);

-- Создание таблицы боевых юнитов
CREATE TABLE battle_units (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    user_unit_id INTEGER NOT NULL REFERENCES user_units(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES game_users(id) ON DELETE CASCADE,
    position_x INTEGER NOT NULL,
    position_y INTEGER NOT NULL,
    total_count INTEGER NOT NULL,
    remaining_hp INTEGER NOT NULL,
    morale NUMERIC(10, 2) NOT NULL DEFAULT 0,
    fatigue NUMERIC(10, 2) NOT NULL DEFAULT 0,
    has_moved INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT positive_x CHECK (position_x >= 0),
    CONSTRAINT positive_y CHECK (position_y >= 0),
    CONSTRAINT positive_count CHECK (total_count > 0),
    CONSTRAINT non_negative_hp CHECK (remaining_hp >= 0)
);

CREATE INDEX idx_battle_units_game_id ON battle_units(game_id);
CREATE INDEX idx_battle_units_player_id ON battle_units(player_id);

-- +goose Down
DROP TABLE IF EXISTS battle_units CASCADE;
DROP TABLE IF EXISTS games CASCADE;
DROP TYPE IF EXISTS game_status CASCADE;
DROP TABLE IF EXISTS fields CASCADE;
DROP TABLE IF EXISTS user_units CASCADE;
DROP TABLE IF EXISTS units CASCADE;
DROP TABLE IF EXISTS game_users CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS users CASCADE;
