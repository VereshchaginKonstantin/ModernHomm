-- +goose Up
-- +goose StatementBegin
ALTER TABLE game_users ADD COLUMN password_hash VARCHAR(255);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE game_users DROP COLUMN password_hash;
-- +goose StatementEnd
