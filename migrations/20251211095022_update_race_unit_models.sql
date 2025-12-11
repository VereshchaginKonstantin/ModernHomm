-- +goose Up
-- +goose StatementBegin

-- Удаляем image_path из race_units
ALTER TABLE race_units DROP COLUMN IF EXISTS image_path;

-- Добавляем диапазон престижа в race_units
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS prestige_min INTEGER NOT NULL DEFAULT 0;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS prestige_max INTEGER NOT NULL DEFAULT 100;

COMMENT ON COLUMN race_units.prestige_min IS 'Минимальный престиж для найма юнита';
COMMENT ON COLUMN race_units.prestige_max IS 'Максимальный престиж для найма юнита';

-- Удаляем icon и image_path из race_unit_skins
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS icon;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS image_path;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Восстанавливаем image_path в race_units
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS image_path VARCHAR(512);

-- Удаляем диапазон престижа из race_units
ALTER TABLE race_units DROP COLUMN IF EXISTS prestige_min;
ALTER TABLE race_units DROP COLUMN IF EXISTS prestige_max;

-- Восстанавливаем icon и image_path в race_unit_skins
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS icon VARCHAR(10) NOT NULL DEFAULT '🎮';
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS image_path VARCHAR(512);

-- +goose StatementEnd
