-- +goose Up
-- +goose StatementBegin
ALTER TABLE game_logs ADD COLUMN IF NOT EXISTS game_state TEXT;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE game_logs DROP COLUMN IF EXISTS game_state;
-- +goose StatementEnd
