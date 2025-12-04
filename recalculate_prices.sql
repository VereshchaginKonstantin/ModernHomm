-- Скрипт для пересчета стоимостей всех юнитов с новой формулой
-- Формула: (damage + defense + health + 100*range + 50*speed + 10000*luck + 10000*crit_chance + 10000*dodge_chance + 10000*counterattack_chance) / 20
-- Если камикадзе: дополнительно делить на 10

UPDATE units
SET price = ROUND(
    CASE
        WHEN is_kamikaze = 1 THEN
            (damage + defense + health + 100 * range + 50 * speed +
             10000 * luck + 10000 * crit_chance + 10000 * dodge_chance + 10000 * counterattack_chance) / 10.0 / 20.0
        ELSE
            (damage + defense + health + 100 * range + 50 * speed +
             10000 * luck + 10000 * crit_chance + 10000 * dodge_chance + 10000 * counterattack_chance) / 20.0
    END,
    2
);

-- Показать результаты
SELECT id, name,
       ROUND((damage + defense + health + 100 * range + 50 * speed +
              10000 * luck + 10000 * crit_chance + 10000 * dodge_chance + 10000 * counterattack_chance) /
              CASE WHEN is_kamikaze = 1 THEN 10.0 ELSE 1.0 END / 20.0, 2) as calculated_price,
       price as actual_price
FROM units
ORDER BY id;
