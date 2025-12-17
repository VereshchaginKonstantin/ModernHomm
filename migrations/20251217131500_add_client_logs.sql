-- +goose Up
-- +goose StatementBegin

-- Таблица для хранения логов клиента Godot
CREATE TABLE IF NOT EXISTS client_logs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    player_id INTEGER,
    level VARCHAR(20) NOT NULL DEFAULT 'info',
    message TEXT NOT NULL,
    context TEXT,
    user_agent VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_client_logs_session_id ON client_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_client_logs_player_id ON client_logs(player_id);
CREATE INDEX IF NOT EXISTS idx_client_logs_created_at ON client_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_client_logs_level ON client_logs(level);

-- Добавляем настройку debugMode в таблицу config (по умолчанию включен)
INSERT INTO config (key, value, description, created_at, updated_at)
VALUES ('debug_mode', 'true', 'Включить/выключить отправку логов с клиента Godot', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (key) DO NOTHING;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

DELETE FROM config WHERE key = 'debug_mode';
DROP TABLE IF EXISTS client_logs;

-- +goose StatementEnd
