-- +goose Up
-- Добавление колонки icon в таблицу units
ALTER TABLE units ADD COLUMN icon VARCHAR(10) NOT NULL DEFAULT '🎮';

-- +goose Down
ALTER TABLE units DROP COLUMN icon;
