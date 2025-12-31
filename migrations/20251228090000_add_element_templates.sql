-- +goose Up
-- Шаблоны препятствий (можно использовать в редакторе полей)
CREATE TABLE IF NOT EXISTS obstacle_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    width INTEGER NOT NULL DEFAULT 1,  -- Ширина в клетках (1, 2, 3, 4)
    height INTEGER NOT NULL DEFAULT 1, -- Высота в клетках (1, 2, 3, 4)
    sprite_data BYTEA,
    sprite_mime_type VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Шаблоны декораций (можно использовать в редакторе полей)
CREATE TABLE IF NOT EXISTS decoration_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    decoration_type decoration_type NOT NULL DEFAULT 'custom',
    width INTEGER NOT NULL DEFAULT 1,  -- Ширина в клетках
    height INTEGER NOT NULL DEFAULT 1, -- Высота в клетках
    sprite_data BYTEA,
    sprite_mime_type VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Добавляем ссылку на шаблон в battle_field_obstacles
ALTER TABLE battle_field_obstacles
ADD COLUMN IF NOT EXISTS obstacle_template_id INTEGER REFERENCES obstacle_templates(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS width INTEGER NOT NULL DEFAULT 1,
ADD COLUMN IF NOT EXISTS height INTEGER NOT NULL DEFAULT 1;

-- Добавляем ссылку на шаблон в battle_field_decorations
ALTER TABLE battle_field_decorations
ADD COLUMN IF NOT EXISTS decoration_template_id INTEGER REFERENCES decoration_templates(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS width INTEGER NOT NULL DEFAULT 1,
ADD COLUMN IF NOT EXISTS height INTEGER NOT NULL DEFAULT 1;

-- Индексы
CREATE INDEX IF NOT EXISTS idx_obstacle_templates_active ON obstacle_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_decoration_templates_active ON decoration_templates(is_active);

-- +goose Down
DROP INDEX IF EXISTS idx_decoration_templates_active;
DROP INDEX IF EXISTS idx_obstacle_templates_active;

ALTER TABLE battle_field_decorations
DROP COLUMN IF EXISTS decoration_template_id,
DROP COLUMN IF EXISTS width,
DROP COLUMN IF EXISTS height;

ALTER TABLE battle_field_obstacles
DROP COLUMN IF EXISTS obstacle_template_id,
DROP COLUMN IF EXISTS width,
DROP COLUMN IF EXISTS height;

DROP TABLE IF EXISTS decoration_templates;
DROP TABLE IF EXISTS obstacle_templates;
