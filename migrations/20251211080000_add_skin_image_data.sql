-- +goose Up
-- +goose StatementBegin

-- Добавление колонок для хранения изображения в БД
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS image_data BYTEA;
ALTER TABLE race_unit_skins ADD COLUMN IF NOT EXISTS image_mime_type VARCHAR(50);

COMMENT ON COLUMN race_unit_skins.image_data IS 'Бинарные данные изображения скина';
COMMENT ON COLUMN race_unit_skins.image_mime_type IS 'MIME тип изображения (image/png, image/jpeg)';

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS image_data;
ALTER TABLE race_unit_skins DROP COLUMN IF EXISTS image_mime_type;

-- +goose StatementEnd
