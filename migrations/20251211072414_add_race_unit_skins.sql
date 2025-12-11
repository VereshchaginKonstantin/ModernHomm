-- +goose Up
-- +goose StatementBegin

-- Создание таблицы скинов юнитов расы
CREATE TABLE IF NOT EXISTS race_unit_skins (
    id SERIAL PRIMARY KEY,
    race_unit_id INTEGER NOT NULL REFERENCES race_units(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(10) NOT NULL DEFAULT '🎮',
    image_path VARCHAR(512),
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_race_unit_skins_race_unit_id ON race_unit_skins(race_unit_id);

-- Добавление колонки skin_id в user_race_units (пока nullable для миграции существующих данных)
ALTER TABLE user_race_units ADD COLUMN IF NOT EXISTS skin_id INTEGER REFERENCES race_unit_skins(id) ON DELETE RESTRICT;

-- Добавление уникального ограничения на user_race_id + race_unit_id
-- (один юнит расы на пользовательскую расу)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'unique_user_race_unit'
    ) THEN
        ALTER TABLE user_race_units ADD CONSTRAINT unique_user_race_unit UNIQUE (user_race_id, race_unit_id);
    END IF;
END $$;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Удаление уникального ограничения
ALTER TABLE user_race_units DROP CONSTRAINT IF EXISTS unique_user_race_unit;

-- Удаление колонки skin_id
ALTER TABLE user_race_units DROP COLUMN IF EXISTS skin_id;

-- Удаление таблицы скинов
DROP TABLE IF EXISTS race_unit_skins;

-- +goose StatementEnd
