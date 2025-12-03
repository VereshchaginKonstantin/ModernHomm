-- +goose Up
-- SQL в этой секции выполняется при применении миграции
ALTER TABLE units ADD COLUMN counterattack_chance NUMERIC(5, 4) NOT NULL DEFAULT 0;

COMMENT ON COLUMN units.counterattack_chance IS 'Доля контратаки (0-1): при получении урона наносит ответный урон с этим коэффициентом';

-- +goose Down
-- SQL в этой секции выполняется при откате миграции
ALTER TABLE units DROP COLUMN counterattack_chance;
