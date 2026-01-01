-- +goose Up
-- +goose StatementBegin

-- Добавляем поле для подсчёта ходов без урона (механика ничьей)
-- Если 5 ходов подряд нет урона - объявляется ничья

ALTER TABLE games ADD COLUMN IF NOT EXISTS turns_without_damage INTEGER NOT NULL DEFAULT 0;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

ALTER TABLE games DROP COLUMN IF EXISTS turns_without_damage;

-- +goose StatementEnd
