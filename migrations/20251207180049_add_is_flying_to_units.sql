-- +goose Up
-- +goose StatementBegin
ALTER TABLE units ADD COLUMN is_flying INTEGER NOT NULL DEFAULT 0;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE units DROP COLUMN is_flying;
-- +goose StatementEnd
