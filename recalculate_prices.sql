-- Скрипт для пересчета стоимостей всех юнитов с новой формулой
-- Формула: (damage + defense + health + 100*range + 100*speed + 1000*luck + 1000*crit_chance + 5000*dodge_chance + 1000*counterattack_chance)
-- Для камикадзе: урон делится на 5, уклонение делится на 50

UPDATE units
SET price = ROUND(
    CASE
        WHEN is_kamikaze = 1 THEN
            (damage / 5.0 + defense + health + 100 * range + 100 * speed +
             1000 * luck + 1000 * crit_chance + (5000 / 50.0) * dodge_chance + 1000 * counterattack_chance)
        ELSE
            (damage + defense + health + 100 * range + 100 * speed +
             1000 * luck + 1000 * crit_chance + 5000 * dodge_chance + 1000 * counterattack_chance)
    END,
    2
);

-- Показать результаты
SELECT id, name,
       ROUND(
           CASE
               WHEN is_kamikaze = 1 THEN
                   (damage / 5.0 + defense + health + 100 * range + 100 * speed +
                    1000 * luck + 1000 * crit_chance + (5000 / 50.0) * dodge_chance + 1000 * counterattack_chance)
               ELSE
                   (damage + defense + health + 100 * range + 100 * speed +
                    1000 * luck + 1000 * crit_chance + 5000 * dodge_chance + 1000 * counterattack_chance)
           END,
           2
       ) as calculated_price,
       price as actual_price
FROM units
ORDER BY id;
