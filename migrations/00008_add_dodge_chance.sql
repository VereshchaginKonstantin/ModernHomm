-- +goose Up
-- SQL в этой секции выполняется при применении миграции
ALTER TABLE units ADD COLUMN dodge_chance NUMERIC(5, 4) NOT NULL DEFAULT 0;

COMMENT ON COLUMN units.dodge_chance IS 'Вероятность уклонения от удара (0-1, где 1 = 100%)';

-- +goose Down
-- SQL в этой секции выполняется при откате миграции
ALTER TABLE units DROP COLUMN dodge_chance;
