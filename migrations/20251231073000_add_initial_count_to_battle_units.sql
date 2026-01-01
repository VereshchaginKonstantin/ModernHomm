-- +goose Up
-- +goose StatementBegin

-- Добавляем поле initial_count в battle_units для хранения начального количества юнитов
-- Это необходимо для правильного расчета наград в челленджах, где army_unit_id = NULL

ALTER TABLE battle_units ADD COLUMN IF NOT EXISTS initial_count INTEGER NOT NULL DEFAULT 1;

-- Обновляем существующие записи - устанавливаем initial_count равным total_count
UPDATE battle_units SET initial_count = total_count WHERE initial_count = 1 AND total_count > 1;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

ALTER TABLE battle_units DROP COLUMN IF EXISTS initial_count;

-- +goose StatementEnd
