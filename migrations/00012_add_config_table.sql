-- +goose Up
-- SQL в этой секции выполняется при применении миграции
CREATE TABLE IF NOT EXISTS config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Создать индекс для быстрого поиска по ключу
CREATE INDEX idx_config_key ON config(key);

-- Добавить начальное значение для стартовой суммы при регистрации
INSERT INTO config (key, value, description) VALUES
    ('start_registration_amount', '1000', 'Стартовая сумма денег при регистрации нового пользователя')
ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE config IS 'Таблица конфигурации приложения';
COMMENT ON COLUMN config.key IS 'Уникальный ключ конфигурации';
COMMENT ON COLUMN config.value IS 'Значение конфигурации (хранится как текст)';

-- +goose Down
-- SQL в этой секции выполняется при откате миграции
DROP TABLE IF EXISTS config;
