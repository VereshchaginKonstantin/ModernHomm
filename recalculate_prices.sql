-- Скрипт для пересчета стоимостей всех юнитов с новой формулой
-- Формула: (damage + 5*defense + health + 100*range + 50*speed + 1000*luck + 1000*crit_chance + 50000*dodge_chance + 1000*counterattack_chance) / 10
-- Если камикадзе: дополнительно делить на 5

UPDATE units
SET price = ROUND(
    CASE
        WHEN is_kamikaze = 1 THEN
            (damage + 5 * defense + health + 100 * range + 50 * speed +
             1000 * luck + 1000 * crit_chance + 50000 * dodge_chance + 1000 * counterattack_chance) / 5.0 / 10.0
        ELSE
            (damage + 5 * defense + health + 100 * range + 50 * speed +
             1000 * luck + 1000 * crit_chance + 50000 * dodge_chance + 1000 * counterattack_chance) / 10.0
    END,
    2
);

-- Показать результаты
SELECT id, name,
       ROUND((damage + 5 * defense + health + 100 * range + 50 * speed +
              1000 * luck + 1000 * crit_chance + 50000 * dodge_chance + 1000 * counterattack_chance) /
              CASE WHEN is_kamikaze = 1 THEN 5.0 ELSE 1.0 END / 10.0, 2) as calculated_price,
       price as actual_price
FROM units
ORDER BY id;
