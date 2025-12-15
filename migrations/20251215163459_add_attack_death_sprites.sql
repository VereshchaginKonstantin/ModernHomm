-- +goose Up
-- +goose StatementBegin

-- Добавляем поля для спрайтов анимации атаки
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS attack_image_data BYTEA;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS attack_image_mime_type VARCHAR(50);
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS attack_sprite_data BYTEA;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS attack_sprite_mime_type VARCHAR(50);
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS attack_frame_count INTEGER NOT NULL DEFAULT 1;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS attack_fps INTEGER NOT NULL DEFAULT 10;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS attack_columns INTEGER NOT NULL DEFAULT 1;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS attack_rows INTEGER NOT NULL DEFAULT 1;

-- Добавляем поля для спрайтов анимации смерти
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS death_image_data BYTEA;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS death_image_mime_type VARCHAR(50);
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS death_sprite_data BYTEA;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS death_sprite_mime_type VARCHAR(50);
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS death_frame_count INTEGER NOT NULL DEFAULT 1;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS death_fps INTEGER NOT NULL DEFAULT 10;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS death_columns INTEGER NOT NULL DEFAULT 1;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS death_rows INTEGER NOT NULL DEFAULT 1;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS attack_image_data;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS attack_image_mime_type;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS attack_sprite_data;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS attack_sprite_mime_type;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS attack_frame_count;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS attack_fps;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS attack_columns;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS attack_rows;

ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS death_image_data;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS death_image_mime_type;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS death_sprite_data;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS death_sprite_mime_type;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS death_frame_count;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS death_fps;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS death_columns;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS death_rows;

-- +goose StatementEnd
