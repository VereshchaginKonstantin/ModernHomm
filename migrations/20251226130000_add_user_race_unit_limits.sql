-- +goose Up
-- +goose StatementBegin

-- Таблица лимитов найма юнитов для каждой расы пользователя
-- Хранит разблокировку уровней и скорость найма отдельно для каждой расы
CREATE TABLE IF NOT EXISTS user_race_unit_limits (
    id SERIAL PRIMARY KEY,
    user_race_id INTEGER NOT NULL REFERENCES user_races(id) ON DELETE CASCADE,
    unit_level_id INTEGER NOT NULL REFERENCES unit_levels(id) ON DELETE CASCADE,

    available_count INTEGER NOT NULL DEFAULT 0,  -- Доступно для найма юнитов данного уровня
    daily_speed INTEGER NOT NULL DEFAULT 1,  -- Юнитов в день (может быть увеличена покупкой)
    level_unlocked BOOLEAN NOT NULL DEFAULT FALSE,  -- Уровень разблокирован для найма
    accumulated_fraction NUMERIC(10, 6) NOT NULL DEFAULT 0,  -- Накопленная дробная часть для почасового начисления

    last_accumulate_at TIMESTAMP NOT NULL DEFAULT NOW(),  -- Когда последний раз накапливались юниты
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_user_race_unit_limit UNIQUE (user_race_id, unit_level_id)
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_user_race_unit_limits_user_race_id ON user_race_unit_limits(user_race_id);
CREATE INDEX IF NOT EXISTS idx_user_race_unit_limits_unit_level_id ON user_race_unit_limits(unit_level_id);
CREATE INDEX IF NOT EXISTS idx_user_race_unit_limits_last_accumulate ON user_race_unit_limits(last_accumulate_at);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

DROP TABLE IF EXISTS user_race_unit_limits;

-- +goose StatementEnd
