-- +goose Up
-- +goose StatementBegin

-- Добавляем колонку obstacle_template_id в таблицу obstacles
ALTER TABLE obstacles ADD COLUMN IF NOT EXISTS obstacle_template_id INTEGER REFERENCES obstacle_templates(id) ON DELETE SET NULL;

-- Создаём таблицу game_decorations для хранения декораций в игре
CREATE TABLE IF NOT EXISTS game_decorations (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    decoration_template_id INTEGER REFERENCES decoration_templates(id) ON DELETE SET NULL,
    decoration_type VARCHAR(20) NOT NULL DEFAULT 'custom',
    position_x INTEGER NOT NULL,
    position_y INTEGER NOT NULL,
    width INTEGER NOT NULL DEFAULT 1,
    height INTEGER NOT NULL DEFAULT 1,
    z_index INTEGER NOT NULL DEFAULT 0
);

-- Индекс для быстрого поиска декораций по game_id
CREATE INDEX IF NOT EXISTS idx_game_decorations_game_id ON game_decorations(game_id);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

DROP TABLE IF EXISTS game_decorations;
ALTER TABLE obstacles DROP COLUMN IF EXISTS obstacle_template_id;

-- +goose StatementEnd
