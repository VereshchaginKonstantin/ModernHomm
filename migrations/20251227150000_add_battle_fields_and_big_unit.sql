-- +goose Up
-- +goose StatementBegin

-- Таблица шаблонов боевых полей (предустановленные поля)
CREATE TABLE IF NOT EXISTS battle_field_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,  -- Название поля
    description TEXT,  -- Описание поля
    field_size_id INTEGER NOT NULL REFERENCES fields(id) ON DELETE RESTRICT,  -- Размер поля (5x5, 7x7, 10x10)
    is_active BOOLEAN NOT NULL DEFAULT TRUE,  -- Активно ли поле для выбора
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы для поиска
CREATE INDEX IF NOT EXISTS idx_battle_field_templates_size ON battle_field_templates(field_size_id);
CREATE INDEX IF NOT EXISTS idx_battle_field_templates_active ON battle_field_templates(is_active);

-- Таблица препятствий на шаблоне поля
CREATE TABLE IF NOT EXISTS battle_field_obstacles (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES battle_field_templates(id) ON DELETE CASCADE,
    position_x INTEGER NOT NULL,  -- Позиция X внутри поля
    position_y INTEGER NOT NULL,  -- Позиция Y внутри поля
    sprite_data BYTEA,  -- Спрайт препятствия (изображение)
    sprite_mime_type VARCHAR(50),  -- MIME тип спрайта
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT positive_obstacle_pos CHECK (position_x >= 0 AND position_y >= 0)
);

CREATE INDEX IF NOT EXISTS idx_battle_field_obstacles_template ON battle_field_obstacles(template_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_battle_field_obstacles_pos ON battle_field_obstacles(template_id, position_x, position_y);

-- Типы декоративных элементов
CREATE TYPE decoration_type AS ENUM ('tree', 'river', 'rock', 'bush', 'flower', 'custom');

-- Таблица декоративных элементов вокруг поля
CREATE TABLE IF NOT EXISTS battle_field_decorations (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES battle_field_templates(id) ON DELETE CASCADE,
    decoration_type decoration_type NOT NULL DEFAULT 'tree',  -- Тип декорации
    position_x INTEGER NOT NULL,  -- Позиция X (может быть отрицательной - за пределами поля)
    position_y INTEGER NOT NULL,  -- Позиция Y (может быть отрицательной - за пределами поля)
    sprite_data BYTEA,  -- Спрайт декорации
    sprite_mime_type VARCHAR(50),  -- MIME тип спрайта
    z_index INTEGER NOT NULL DEFAULT 0,  -- Порядок отрисовки
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_battle_field_decorations_template ON battle_field_decorations(template_id);
CREATE INDEX IF NOT EXISTS idx_battle_field_decorations_type ON battle_field_decorations(decoration_type);

-- Добавляем флаг "большой юнит" в race_units (занимает 4 клетки - 2x2)
ALTER TABLE race_units ADD COLUMN IF NOT EXISTS is_big BOOLEAN NOT NULL DEFAULT FALSE;

-- Добавляем комментарий к полю
COMMENT ON COLUMN race_units.is_big IS 'Большой юнит занимает 4 клетки (2x2)';

-- Связь игры с шаблоном поля (для загрузки препятствий и декораций)
ALTER TABLE games ADD COLUMN IF NOT EXISTS battle_field_template_id INTEGER REFERENCES battle_field_templates(id) ON DELETE SET NULL;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Удаляем связь игры с шаблоном
ALTER TABLE games DROP COLUMN IF EXISTS battle_field_template_id;

-- Удаляем флаг большого юнита
ALTER TABLE race_units DROP COLUMN IF EXISTS is_big;

-- Удаляем таблицы в обратном порядке
DROP TABLE IF EXISTS battle_field_decorations;
DROP TYPE IF EXISTS decoration_type;
DROP TABLE IF EXISTS battle_field_obstacles;
DROP TABLE IF EXISTS battle_field_templates;

-- +goose StatementEnd
