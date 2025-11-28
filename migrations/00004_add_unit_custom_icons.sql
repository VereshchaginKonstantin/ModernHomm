-- +goose Up
-- +goose StatementBegin
CREATE TABLE IF NOT EXISTS unit_custom_icons (
    id SERIAL PRIMARY KEY,
    unit_id INTEGER NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    custom_icon VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(unit_id)
);

CREATE INDEX idx_unit_custom_icons_unit_id ON unit_custom_icons(unit_id);

COMMENT ON TABLE unit_custom_icons IS 'Таблица для хранения пользовательских иконок юнитов';
COMMENT ON COLUMN unit_custom_icons.unit_id IS 'ID типа юнита';
COMMENT ON COLUMN unit_custom_icons.custom_icon IS 'Пользовательская иконка (эмодзи)';
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE IF EXISTS unit_custom_icons;
-- +goose StatementEnd
