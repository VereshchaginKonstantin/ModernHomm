-- +goose Up
-- Добавление unique constraint для username
DROP INDEX IF EXISTS idx_game_users_username;
CREATE UNIQUE INDEX idx_game_users_username_unique ON game_users(username);

-- +goose Down
-- Удаление unique constraint и восстановление обычного индекса
DROP INDEX IF EXISTS idx_game_users_username_unique;
CREATE INDEX idx_game_users_username ON game_users(username);
