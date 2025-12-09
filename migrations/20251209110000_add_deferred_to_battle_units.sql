-- +goose Up
-- Добавление поля deferred для отложенных юнитов
ALTER TABLE battle_units ADD COLUMN IF NOT EXISTS deferred INTEGER NOT NULL DEFAULT 0;

-- +goose Down
ALTER TABLE battle_units DROP COLUMN IF EXISTS deferred;
