-- +goose Up
-- +goose StatementBegin

-- Удаляем колонку icon из race_units
ALTER TABLE race_units DROP COLUMN IF EXISTS icon;

-- Добавляем колонку icon в unit_levels
ALTER TABLE unit_levels ADD COLUMN IF NOT EXISTS icon VARCHAR(10) NOT NULL DEFAULT '🎮';

COMMENT ON COLUMN unit_levels.icon IS 'Иконка уровня юнита';

-- Делаем unit_level_id обязательным в race_units
-- Сначала обновляем NULL значения, если есть
UPDATE race_units SET unit_level_id = (SELECT id FROM unit_levels WHERE level = 1 LIMIT 1) WHERE unit_level_id IS NULL;
ALTER TABLE race_units ALTER COLUMN unit_level_id SET NOT NULL;

-- Добавляем уникальный constraint на (race_id, unit_level_id)
ALTER TABLE race_units ADD CONSTRAINT unique_race_unit_level UNIQUE (race_id, unit_level_id);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Удаляем уникальный constraint
ALTER TABLE race_units DROP CONSTRAINT IF EXISTS unique_race_unit_level;

-- Делаем unit_level_id необязательным
ALTER TABLE race_units ALTER COLUMN unit_level_id DROP NOT NULL;

-- Удаляем icon из unit_levels
ALTER TABLE unit_levels DROP COLUMN IF EXISTS icon;

-- Восстанавливаем icon в race_units
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS icon VARCHAR(10) NOT NULL DEFAULT '🎮';

-- +goose StatementEnd
