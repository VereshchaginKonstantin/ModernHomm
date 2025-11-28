-- +goose Up
-- +goose StatementBegin
ALTER TABLE units ADD COLUMN image_path VARCHAR(512);

COMMENT ON COLUMN units.image_path IS 'Путь к изображению юнита для отображения на поле';
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE units DROP COLUMN IF EXISTS image_path;
-- +goose StatementEnd
