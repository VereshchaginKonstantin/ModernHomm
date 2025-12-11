-- +goose Up
-- +goose StatementBegin

-- Удаляем старые данные из unit_levels (они привязаны к расам)
DELETE FROM unit_levels;

-- Удаляем колонки race_id и cost из unit_levels
ALTER TABLE unit_levels DROP COLUMN IF EXISTS race_id;
ALTER TABLE unit_levels DROP COLUMN IF EXISTS cost;

-- Добавляем диапазон престижа в unit_levels
ALTER TABLE unit_levels ADD COLUMN IF NOT EXISTS prestige_min INTEGER NOT NULL DEFAULT 0;
ALTER TABLE unit_levels ADD COLUMN IF NOT EXISTS prestige_max INTEGER NOT NULL DEFAULT 100;

-- Делаем level уникальным
ALTER TABLE unit_levels ADD CONSTRAINT unit_levels_level_unique UNIQUE (level);

COMMENT ON COLUMN unit_levels.prestige_min IS 'Минимальный престиж для найма юнита этого уровня';
COMMENT ON COLUMN unit_levels.prestige_max IS 'Максимальный престиж для найма юнита этого уровня';

-- Заполняем справочник уровней (1-7) с диапазонами престижа
INSERT INTO unit_levels (level, prestige_min, prestige_max, created_at) VALUES
    (1, 0, 100, NOW()),
    (2, 100, 300, NOW()),
    (3, 300, 600, NOW()),
    (4, 600, 1000, NOW()),
    (5, 1000, 1500, NOW()),
    (6, 1500, 2500, NOW()),
    (7, 2500, 5000, NOW());

-- Удаляем prestige_min и prestige_max из race_units, добавляем ссылку на unit_level
ALTER TABLE race_units DROP COLUMN IF EXISTS prestige_min;
ALTER TABLE race_units DROP COLUMN IF EXISTS prestige_max;
ALTER TABLE race_units DROP COLUMN IF EXISTS level;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS unit_level_id INTEGER REFERENCES unit_levels(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS ix_race_units_unit_level_id ON race_units(unit_level_id);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Удаляем ссылку на unit_level из race_units
ALTER TABLE race_units DROP COLUMN IF EXISTS unit_level_id;

-- Восстанавливаем prestige_min и prestige_max в race_units
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 1;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS prestige_min INTEGER NOT NULL DEFAULT 0;
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS prestige_max INTEGER NOT NULL DEFAULT 100;

-- Удаляем prestige из unit_levels
ALTER TABLE unit_levels DROP COLUMN IF EXISTS prestige_min;
ALTER TABLE unit_levels DROP COLUMN IF EXISTS prestige_max;

-- Восстанавливаем race_id и cost в unit_levels
ALTER TABLE unit_levels DROP CONSTRAINT IF EXISTS unit_levels_level_unique;
ALTER TABLE unit_levels ADD COLUMN IF NOT EXISTS race_id INTEGER REFERENCES game_races(id) ON DELETE CASCADE;
ALTER TABLE unit_levels ADD COLUMN IF NOT EXISTS cost NUMERIC(10, 2) NOT NULL DEFAULT 100;

-- +goose StatementEnd
