-- Скрипт для пересчета стоимостей всех юнитов с новой формулой
-- Формула: (damage + defense + health + 100*range + 100*speed + 1000*luck + 1000*crit_chance + 1000*dodge_chance + 100*counterattack_chance)
-- Для камикадзе: уклонение не учитывается

UPDATE units
SET price = ROUND(
    CASE
        WHEN is_kamikaze = 1 THEN
            (damage + defense + health + 100 * range + 100 * speed +
             1000 * luck + 1000 * crit_chance + 0 * dodge_chance + 100 * counterattack_chance)
        ELSE
            (damage + defense + health + 100 * range + 100 * speed +
             1000 * luck + 1000 * crit_chance + 1000 * dodge_chance + 100 * counterattack_chance)
    END,
    2
);

-- Показать результаты
SELECT id, name,
       ROUND(
           CASE
               WHEN is_kamikaze = 1 THEN
                   (damage + defense + health + 100 * range + 100 * speed +
                    1000 * luck + 1000 * crit_chance + 0 * dodge_chance + 100 * counterattack_chance)
               ELSE
                   (damage + defense + health + 100 * range + 100 * speed +
                    1000 * luck + 1000 * crit_chance + 1000 * dodge_chance + 100 * counterattack_chance)
           END,
           2
       ) as calculated_price,
       price as actual_price
FROM units
ORDER BY id;
