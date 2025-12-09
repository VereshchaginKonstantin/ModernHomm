-- +goose Up
-- Удаление колонок first_name и last_name из таблицы users
-- Вся идентификация теперь происходит через username

ALTER TABLE users DROP COLUMN IF EXISTS first_name;
ALTER TABLE users DROP COLUMN IF EXISTS last_name;

-- +goose Down
-- Восстановление колонок first_name и last_name
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(255);
