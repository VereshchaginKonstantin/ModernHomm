-- +goose Up
-- Создание таблицы сеттингов (расс)
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    is_tournament BOOLEAN NOT NULL DEFAULT FALSE,
    unlock_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    subscription_only BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Создание индекса для поиска по названию
CREATE INDEX idx_settings_name ON settings(name);

-- Создание таблицы изображений юнитов
CREATE TABLE unit_images (
    id SERIAL PRIMARY KEY,
    description TEXT,

    -- Параметры применимости
    is_flying BOOLEAN,
    is_kamikaze BOOLEAN,
    min_damage INTEGER,
    max_damage INTEGER,
    min_defense INTEGER,
    max_defense INTEGER,

    -- Изображение
    image_data BYTEA NOT NULL,

    -- Связь с сеттингом
    setting_id INTEGER NOT NULL REFERENCES settings(id) ON DELETE CASCADE,

    -- Стоимость и доступность
    coin_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    subscription_only BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Создание индексов
CREATE INDEX idx_unit_images_setting_id ON unit_images(setting_id);
CREATE INDEX idx_unit_images_is_flying ON unit_images(is_flying);
CREATE INDEX idx_unit_images_is_kamikaze ON unit_images(is_kamikaze);

-- +goose Down
-- Удаление таблиц
DROP TABLE IF EXISTS unit_images;
DROP TABLE IF EXISTS settings;
