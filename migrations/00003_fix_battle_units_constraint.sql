-- +goose Up
-- Исправление constraint для battle_units - разрешаем total_count = 0 для убитых юнитов
ALTER TABLE battle_units DROP CONSTRAINT IF EXISTS positive_count;
ALTER TABLE battle_units ADD CONSTRAINT positive_count CHECK (total_count >= 0);

-- +goose Down
-- Откат изменений
ALTER TABLE battle_units DROP CONSTRAINT IF EXISTS positive_count;
ALTER TABLE battle_units ADD CONSTRAINT positive_count CHECK (total_count > 0);
