-- +goose Up
-- +goose StatementBegin
ALTER TABLE units ADD COLUMN effective_against_unit_id INTEGER REFERENCES units(id) ON DELETE SET NULL;

COMMENT ON COLUMN units.effective_against_unit_id IS 'ID юнита, против которого этот юнит эффективен (наносит x1.5 урона)';
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE units DROP COLUMN IF EXISTS effective_against_unit_id;
-- +goose StatementEnd
