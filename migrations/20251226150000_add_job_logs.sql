-- +goose Up
-- +goose StatementBegin

-- Таблица логов выполнения джоб
CREATE TABLE IF NOT EXISTS job_logs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,  -- Название джобы
    status VARCHAR(20) NOT NULL DEFAULT 'running',  -- running, success, failed
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP,
    duration_ms INTEGER,  -- Длительность в миллисекундах
    records_processed INTEGER DEFAULT 0,  -- Количество обработанных записей
    error_message TEXT,  -- Сообщение об ошибке если failed
    details JSONB,  -- Дополнительные детали в JSON
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_job_logs_job_name ON job_logs(job_name);
CREATE INDEX IF NOT EXISTS idx_job_logs_status ON job_logs(status);
CREATE INDEX IF NOT EXISTS idx_job_logs_started_at ON job_logs(started_at DESC);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

DROP TABLE IF EXISTS job_logs;

-- +goose StatementEnd
