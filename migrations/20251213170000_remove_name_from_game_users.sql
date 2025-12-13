-- +goose Up
-- +goose StatementBegin

-- Сначала обновляем username из name для записей, где username NULL
UPDATE game_users SET username = name WHERE username IS NULL;

-- Делаем username NOT NULL
ALTER TABLE game_users ALTER COLUMN username SET NOT NULL;

-- Удаляем колонку name
ALTER TABLE game_users DROP COLUMN IF EXISTS name;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Добавляем колонку name обратно
ALTER TABLE game_users ADD COLUMN name VARCHAR(255);

-- Копируем username в name
UPDATE game_users SET name = username;

-- Делаем name NOT NULL
ALTER TABLE game_users ALTER COLUMN name SET NOT NULL;

-- Делаем username nullable
ALTER TABLE game_users ALTER COLUMN username DROP NOT NULL;

-- +goose StatementEnd
