-- +goose Up
-- +goose StatementBegin

-- Add sprite/texture parameters for Godot Sprite and TextureRect
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_scale_x NUMERIC(10, 4) NOT NULL DEFAULT 1.0;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_scale_y NUMERIC(10, 4) NOT NULL DEFAULT 1.0;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_offset_x INTEGER NOT NULL DEFAULT 0;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_offset_y INTEGER NOT NULL DEFAULT 0;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_rotation NUMERIC(10, 4) NOT NULL DEFAULT 0;

-- Add animated sprite data (for AnimatedSprite2D in Godot)
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_frames_data BYTEA;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_frames_mime_type VARCHAR(50);
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_frame_count INTEGER NOT NULL DEFAULT 1;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_fps INTEGER NOT NULL DEFAULT 10;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_columns INTEGER NOT NULL DEFAULT 1;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS sprite_rows INTEGER NOT NULL DEFAULT 1;

-- Add Godot asset paths
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS godot_texture_path VARCHAR(512);
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS godot_sprite_path VARCHAR(512);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Remove Godot asset paths
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS godot_sprite_path;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS godot_texture_path;

-- Remove animated sprite data
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_rows;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_columns;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_fps;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_frame_count;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_frames_mime_type;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_frames_data;

-- Remove sprite/texture parameters
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_rotation;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_offset_y;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_offset_x;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_scale_y;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS sprite_scale_x;

-- +goose StatementEnd
