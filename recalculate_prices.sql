-- Скрипт для пересчета стоимостей всех юнитов с новой формулой
-- Формула: (Урон + Защита + Здоровье + 2*Дальность*(Урон + Защита) + Скорость*(Урон + Защита) +
--           2*Удача*Урон + 2*Крит*Урон + 10*Уклонение*(Урон + Защита) + 10*Контратака*Урон)
-- Для камикадзе: урон делится на 5, уклонение делится на 50

UPDATE units
SET price = ROUND(
    CASE
        WHEN is_kamikaze = 1 THEN
            ((damage / 5.0) + defense + health +
             2 * range * ((damage / 5.0) + defense) +
             speed * ((damage / 5.0) + defense) +
             2 * luck * (damage / 5.0) +
             2 * crit_chance * (damage / 5.0) +
             10 * (dodge_chance / 50.0) * ((damage / 5.0) + defense) +
             10 * counterattack_chance * (damage / 5.0))
        ELSE
            (damage + defense + health +
             2 * range * (damage + defense) +
             speed * (damage + defense) +
             2 * luck * damage +
             2 * crit_chance * damage +
             10 * dodge_chance * (damage + defense) +
             10 * counterattack_chance * damage)
    END,
    2
);

-- Показать результаты
SELECT id, name,
       ROUND(
           CASE
               WHEN is_kamikaze = 1 THEN
                   ((damage / 5.0) + defense + health +
                    2 * range * ((damage / 5.0) + defense) +
                    speed * ((damage / 5.0) + defense) +
                    2 * luck * (damage / 5.0) +
                    2 * crit_chance * (damage / 5.0) +
                    10 * (dodge_chance / 50.0) * ((damage / 5.0) + defense) +
                    10 * counterattack_chance * (damage / 5.0))
               ELSE
                   (damage + defense + health +
                    2 * range * (damage + defense) +
                    speed * (damage + defense) +
                    2 * luck * damage +
                    2 * crit_chance * damage +
                    10 * dodge_chance * (damage + defense) +
                    10 * counterattack_chance * damage)
           END,
           2
       ) as calculated_price,
       price as actual_price
FROM units
ORDER BY id;
