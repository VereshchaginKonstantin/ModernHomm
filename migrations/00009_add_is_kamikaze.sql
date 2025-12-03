-- +goose Up
-- SQL в этой секции выполняется при применении миграции
ALTER TABLE units ADD COLUMN is_kamikaze INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN units.is_kamikaze IS 'Флаг камикадзе (0 - нет, 1 - да): наносит урон одним юнитом и уменьшается на 1 после атаки';

-- +goose Down
-- SQL в этой секции выполняется при откате миграции
ALTER TABLE units DROP COLUMN is_kamikaze;
