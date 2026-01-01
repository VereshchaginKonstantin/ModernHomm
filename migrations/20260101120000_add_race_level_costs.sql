-- +goose Up
-- +goose StatementBegin

-- Добавляем поля для стоимости разблокировки и улучшения скорости по уровням на уровне расы
ALTER TABLE game_races ADD COLUMN IF NOT EXISTS level_unlock_costs TEXT;
ALTER TABLE game_races ADD COLUMN IF NOT EXISTS speed_upgrade_costs TEXT;

-- Заполняем дефолтными значениями из unit_levels для существующих рас
UPDATE game_races SET 
    level_unlock_costs = '{"1": 0, "2": 0, "3": 50, "4": 100, "5": 200, "6": 500, "7": 1000}',
    speed_upgrade_costs = '{"1": 1, "2": 10, "3": 10, "4": 10, "5": 10, "6": 10, "7": 10}'
WHERE level_unlock_costs IS NULL;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

ALTER TABLE game_races DROP COLUMN IF EXISTS level_unlock_costs;
ALTER TABLE game_races DROP COLUMN IF EXISTS speed_upgrade_costs;

-- +goose StatementEnd
