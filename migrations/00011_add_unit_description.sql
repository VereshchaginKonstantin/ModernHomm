-- +goose Up
-- SQL в этой секции выполняется при применении миграции
ALTER TABLE units ADD COLUMN description VARCHAR(1000) NULL;

COMMENT ON COLUMN units.description IS 'Описание юнита';

-- Добавляем описания для существующих юнитов
UPDATE units SET description = 'Первая линия обороны, но не очень умная. Машет мечом и надеется на лучшее!' WHERE name = 'Мечник';
UPDATE units SET description = 'Стреляет издалека и убегает. Трусость? Нет, тактика!' WHERE name = 'Лучник';
UPDATE units SET description = 'Тяжелая броня, громкий топот, слабое зрение. Где враг? Где конь?' WHERE name = 'Рыцарь';
UPDATE units SET description = 'Бросает файрболы и жалуется на ману. Всегда не хватает!' WHERE name = 'Маг';
UPDATE units SET description = 'Летает, жарит, пугает. Дорого, но эффектно!' WHERE name = 'Дракон';

-- +goose Down
-- SQL в этой секции выполняется при откате миграции
ALTER TABLE units DROP COLUMN description;
