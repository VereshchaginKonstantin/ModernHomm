-- +goose Up
-- Добавление поля username для Telegram username пользователя
ALTER TABLE game_users ADD COLUMN username VARCHAR(255);

-- Создаем индекс для username (будет использоваться для входа в веб-интерфейс)
CREATE INDEX idx_game_users_username ON game_users(username);

-- +goose Down
-- Удаление индекса и поля username
DROP INDEX IF EXISTS idx_game_users_username;
ALTER TABLE game_users DROP COLUMN username;
