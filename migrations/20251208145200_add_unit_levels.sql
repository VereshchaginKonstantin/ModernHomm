-- +goose Up
-- Создание таблицы уровней юнитов
CREATE TABLE unit_levels (
    id SERIAL PRIMARY KEY,
    level INTEGER NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Диапазоны параметров
    min_damage INTEGER NOT NULL DEFAULT 1,
    max_damage INTEGER NOT NULL DEFAULT 10,
    min_defense INTEGER NOT NULL DEFAULT 1,
    max_defense INTEGER NOT NULL DEFAULT 10,
    min_health INTEGER NOT NULL DEFAULT 10,
    max_health INTEGER NOT NULL DEFAULT 100,
    min_speed INTEGER NOT NULL DEFAULT 1,
    max_speed INTEGER NOT NULL DEFAULT 5,
    min_cost NUMERIC(12, 2) NOT NULL DEFAULT 10,
    max_cost NUMERIC(12, 2) NOT NULL DEFAULT 100,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Создание индекса для поиска по уровню
CREATE INDEX idx_unit_levels_level ON unit_levels(level);

-- Добавление связи с уровнем юнита в таблицу изображений
ALTER TABLE unit_images ADD COLUMN unit_level_id INTEGER REFERENCES unit_levels(id) ON DELETE SET NULL;
CREATE INDEX idx_unit_images_unit_level_id ON unit_images(unit_level_id);

-- Удаление лишних полей из unit_images
ALTER TABLE unit_images DROP COLUMN IF EXISTS is_flying;
ALTER TABLE unit_images DROP COLUMN IF EXISTS is_kamikaze;
ALTER TABLE unit_images DROP COLUMN IF EXISTS min_damage;
ALTER TABLE unit_images DROP COLUMN IF EXISTS max_damage;
ALTER TABLE unit_images DROP COLUMN IF EXISTS min_defense;
ALTER TABLE unit_images DROP COLUMN IF EXISTS max_defense;
ALTER TABLE unit_images DROP COLUMN IF EXISTS coin_cost;

-- Удаление индексов на удаленные поля
DROP INDEX IF EXISTS idx_unit_images_is_flying;
DROP INDEX IF EXISTS idx_unit_images_is_kamikaze;

-- Заполнение базовых 7 уровней юнитов
INSERT INTO unit_levels (level, name, description, min_damage, max_damage, min_defense, max_defense, min_health, max_health, min_speed, max_speed, min_cost, max_cost) VALUES
    (1, 'Уровень 1', 'Слабые юниты начального уровня', 1, 3, 1, 2, 5, 15, 1, 2, 10, 30),
    (2, 'Уровень 2', 'Юниты базового уровня', 2, 5, 2, 4, 10, 25, 2, 3, 25, 60),
    (3, 'Уровень 3', 'Юниты среднего уровня', 4, 8, 3, 6, 20, 40, 2, 4, 50, 100),
    (4, 'Уровень 4', 'Сильные юниты', 6, 12, 5, 9, 35, 60, 3, 5, 80, 150),
    (5, 'Уровень 5', 'Элитные юниты', 10, 18, 7, 12, 50, 90, 3, 6, 120, 220),
    (6, 'Уровень 6', 'Высшие юниты', 15, 25, 10, 16, 70, 130, 4, 7, 180, 320),
    (7, 'Уровень 7', 'Легендарные юниты', 20, 35, 14, 22, 100, 200, 5, 8, 280, 500);

-- +goose Down
-- Удаление связи с уровнем юнита из таблицы изображений
DROP INDEX IF EXISTS idx_unit_images_unit_level_id;
ALTER TABLE unit_images DROP COLUMN IF EXISTS unit_level_id;

-- Восстановление удаленных полей в unit_images
ALTER TABLE unit_images ADD COLUMN IF NOT EXISTS is_flying BOOLEAN;
ALTER TABLE unit_images ADD COLUMN IF NOT EXISTS is_kamikaze BOOLEAN;
ALTER TABLE unit_images ADD COLUMN IF NOT EXISTS min_damage INTEGER;
ALTER TABLE unit_images ADD COLUMN IF NOT EXISTS max_damage INTEGER;
ALTER TABLE unit_images ADD COLUMN IF NOT EXISTS min_defense INTEGER;
ALTER TABLE unit_images ADD COLUMN IF NOT EXISTS max_defense INTEGER;
ALTER TABLE unit_images ADD COLUMN IF NOT EXISTS coin_cost NUMERIC(12, 2) NOT NULL DEFAULT 0;

-- Восстановление индексов
CREATE INDEX IF NOT EXISTS idx_unit_images_is_flying ON unit_images(is_flying);
CREATE INDEX IF NOT EXISTS idx_unit_images_is_kamikaze ON unit_images(is_kamikaze);

-- Удаление таблицы уровней юнитов
DROP TABLE IF EXISTS unit_levels;
