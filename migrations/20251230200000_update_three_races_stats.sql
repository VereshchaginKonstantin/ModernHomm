-- +goose Up
-- +goose StatementBegin

-- Обновление характеристик трёх рас с учетом новой формулы стоимости (defense/3 для башен)
-- Версия 2.0 - Финальная

-- =====================================================
-- РАСА 1: ТЁМНАЯ СИЛА (Оборонительная раса)
-- Общая стоимость: 14,791 золота
-- =====================================================

-- Уровень 1: Кикимора прядущая (138 золота)
UPDATE race_units SET
    attack = 5, defense = 12, min_damage = 5, max_damage = 5, health = 22,
    speed = 2, initiative = 10, luck = 0.03, crit_chance = 0.04,
    dodge_chance = 0, counterattack_chance = 0, range = 1,
    regeneration_health = 3, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Тёмная Сила')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 1);

-- Уровень 2: Избушка (БАШНЯ, 834 золота)
UPDATE race_units SET
    name = 'Избушка',
    attack = 25, defense = 60, min_damage = 25, max_damage = 25, health = 65,
    speed = 0, initiative = 0, luck = 0.02, crit_chance = 0.05,
    dodge_chance = 0, counterattack_chance = 0, range = 3,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Тёмная Сила')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 2);

-- Уровень 3: Леший (510 золота)
UPDATE race_units SET
    name = 'Леший',
    attack = 28, defense = 32, min_damage = 28, max_damage = 28, health = 45,
    speed = 2, initiative = 14, luck = 0.05, crit_chance = 0.08,
    dodge_chance = 0, counterattack_chance = 0.35, range = 1,
    regeneration_health = 6, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Тёмная Сила')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 3);

-- Уровень 4: Баба-Яга (Летающая, Яд 6×3, 1066 золота)
UPDATE race_units SET
    name = 'Баба-Яга',
    attack = 38, defense = 30, min_damage = 38, max_damage = 38, health = 52,
    speed = 3, initiative = 17, luck = 0.10, crit_chance = 0.14,
    dodge_chance = 0, counterattack_chance = 0, range = 3,
    is_flying = TRUE,
    regeneration_health = 0, poison_damage = 6, poison_turns = 3
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Тёмная Сила')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 4);

-- Уровень 5: Соловей (КАМИКАДЗЕ, 6043 золота)
UPDATE race_units SET
    name = 'Соловей',
    attack = 2700, defense = 22, min_damage = 2700, max_damage = 2700, health = 45,
    speed = 3, initiative = 19, luck = 0.15, crit_chance = 0.20,
    dodge_chance = 0, counterattack_chance = 0, range = 3,
    is_kamikaze = TRUE,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Тёмная Сила')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 5);

-- Уровень 6: Кощей (Яд 12×5, Регенерация 22, 1998 золота)
UPDATE race_units SET
    name = 'Кощей',
    attack = 55, defense = 72, min_damage = 55, max_damage = 55, health = 140,
    speed = 3, initiative = 18, luck = 0.08, crit_chance = 0.12,
    dodge_chance = 0, counterattack_chance = 0, range = 2,
    regeneration_health = 22, poison_damage = 12, poison_turns = 5
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Тёмная Сила')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 6);

-- Уровень 7: Змей Горыныч (Летающий, Контратака 60%, Яд 15×5, 4202 золота)
UPDATE race_units SET
    attack = 102, defense = 88, min_damage = 102, max_damage = 102, health = 305,
    speed = 4, initiative = 22, luck = 0.14, crit_chance = 0.18,
    dodge_chance = 0, counterattack_chance = 0.60, range = 3,
    is_flying = TRUE, is_big = FALSE,
    regeneration_health = 0, poison_damage = 15, poison_turns = 5
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Тёмная Сила')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 7);

-- =====================================================
-- РАСА 2: ДРУЖИНА РУСИ (Сбалансированная раса)
-- Общая стоимость: 11,724 золота
-- =====================================================

-- Уровень 1: Ополченец-смерд (121 золота)
UPDATE race_units SET
    attack = 11, defense = 9, min_damage = 11, max_damage = 11, health = 18,
    speed = 2, initiative = 11, luck = 0.05, crit_chance = 0.08,
    dodge_chance = 0, counterattack_chance = 0, range = 1,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Дружина Руси')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 1);

-- Уровень 2: Сторожевая вежа (БАШНЯ, 1064 золота)
UPDATE race_units SET
    attack = 28, defense = 62, min_damage = 28, max_damage = 28, health = 68,
    speed = 0, initiative = 0, luck = 0.03, crit_chance = 0.07,
    dodge_chance = 0, counterattack_chance = 0, range = 4,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Дружина Руси')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 2);

-- Уровень 3: Стрелец московский (Дальнобойный, Крит 16%, 640 золота)
UPDATE race_units SET
    attack = 36, defense = 18, min_damage = 36, max_damage = 36, health = 26,
    speed = 2, initiative = 13, luck = 0.12, crit_chance = 0.16,
    dodge_chance = 0, counterattack_chance = 0, range = 4,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Дружина Руси')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 3);

-- Уровень 4: Волхв-ведун (Яд 8×4, Регенерация 10, 1120 золота)
UPDATE race_units SET
    attack = 29, defense = 40, min_damage = 29, max_damage = 29, health = 66,
    speed = 2, initiative = 15, luck = 0.12, crit_chance = 0.10,
    dodge_chance = 0, counterattack_chance = 0, range = 3,
    regeneration_health = 10, poison_damage = 8, poison_turns = 4
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Дружина Руси')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 4);

-- Уровень 5: Опричник царский (Контратака 52%, 1124 золота)
UPDATE race_units SET
    attack = 60, defense = 40, min_damage = 60, max_damage = 60, health = 72,
    speed = 4, initiative = 19, luck = 0.13, crit_chance = 0.20,
    dodge_chance = 0, counterattack_chance = 0.52, range = 1,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Дружина Руси')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 5);

-- Уровень 6: Порохонос-смертник (КАМИКАДЗЕ, 5031 золота)
UPDATE race_units SET
    attack = 2850, defense = 18, min_damage = 2850, max_damage = 2850, health = 42,
    speed = 3, initiative = 18, luck = 0.10, crit_chance = 0.15,
    dodge_chance = 0, counterattack_chance = 0, range = 2,
    is_kamikaze = TRUE,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Дружина Руси')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 6);

-- Уровень 7: Князь (Летающий, Контратака 55%, 2624 золота)
UPDATE race_units SET
    name = 'Князь',
    attack = 92, defense = 62, min_damage = 92, max_damage = 92, health = 200,
    speed = 5, initiative = 23, luck = 0.16, crit_chance = 0.22,
    dodge_chance = 0, counterattack_chance = 0.55, range = 2,
    is_flying = TRUE, is_big = FALSE,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Дружина Руси')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 7);

-- =====================================================
-- РАСА 3: СВЕТЛАЯ СКАЗКА (Атакующая раса)
-- Общая стоимость: 12,687 золота
-- =====================================================

-- Уровень 1: Домовой-хранитель (Регенерация 4, 144 золота)
UPDATE race_units SET
    attack = 6, defense = 11, min_damage = 6, max_damage = 6, health = 17,
    speed = 2, initiative = 12, luck = 0.06, crit_chance = 0.07,
    dodge_chance = 0, counterattack_chance = 0, range = 1,
    regeneration_health = 4, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Светлая Сказка')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 1);

-- Уровень 2: Золотой терем (БАШНЯ, 1112 золота)
UPDATE race_units SET
    attack = 30, defense = 64, min_damage = 30, max_damage = 30, health = 70,
    speed = 0, initiative = 0, luck = 0.05, crit_chance = 0.08,
    dodge_chance = 0, counterattack_chance = 0, range = 4,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Светлая Сказка')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 2);

-- Уровень 3: Серый Волк (Быстрый, Крит 17%, 533 золота)
UPDATE race_units SET
    attack = 38, defense = 22, min_damage = 38, max_damage = 38, health = 32,
    speed = 5, initiative = 18, luck = 0.11, crit_chance = 0.17,
    dodge_chance = 0, counterattack_chance = 0, range = 1,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Светлая Сказка')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 3);

-- Уровень 4: Царевна-Лебедь (Летающая, Регенерация 10, 930 золота)
UPDATE race_units SET
    attack = 32, defense = 27, min_damage = 32, max_damage = 32, health = 44,
    speed = 4, initiative = 19, luck = 0.13, crit_chance = 0.16,
    dodge_chance = 0, counterattack_chance = 0, range = 3,
    is_flying = TRUE,
    regeneration_health = 10, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Светлая Сказка')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 4);

-- Уровень 5: Богатырь Илья (Контратака 55%, 1279 золота)
UPDATE race_units SET
    name = 'Богатырь Илья',
    attack = 70, defense = 53, min_damage = 70, max_damage = 70, health = 108,
    speed = 3, initiative = 17, luck = 0.15, crit_chance = 0.19,
    dodge_chance = 0, counterattack_chance = 0.55, range = 1,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Светлая Сказка')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 5);

-- Уровень 6: Жар-птица (Летающая, Огонь 9×4, 2081 золота)
UPDATE race_units SET
    attack = 74, defense = 39, min_damage = 74, max_damage = 74, health = 80,
    speed = 5, initiative = 22, luck = 0.18, crit_chance = 0.22,
    dodge_chance = 0, counterattack_chance = 0, range = 3,
    is_flying = TRUE,
    regeneration_health = 0, poison_damage = 9, poison_turns = 4
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Светлая Сказка')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 6);

-- Уровень 7: Иван на Коньке (КАМИКАДЗЕ, 6608 золота)
UPDATE race_units SET
    name = 'Иван на Коньке',
    attack = 2750, defense = 48, min_damage = 2750, max_damage = 2750, health = 100,
    speed = 5, initiative = 24, luck = 0.20, crit_chance = 0.28,
    dodge_chance = 0, counterattack_chance = 0, range = 2,
    is_kamikaze = TRUE, is_big = FALSE,
    regeneration_health = 0, poison_damage = 0, poison_turns = 0
WHERE race_id = (SELECT id FROM game_races WHERE name = 'Светлая Сказка')
AND unit_level_id = (SELECT id FROM unit_levels WHERE level = 7);

-- Обновляем имена в скинах, если они изменились
UPDATE race_unit_skins SET
    name = ru.name || ' (базовый)',
    description = 'Базовый скин юнита ' || ru.name
FROM race_units ru
WHERE race_unit_skins.race_unit_id = ru.id
AND ru.race_id IN (SELECT id FROM game_races WHERE name IN ('Тёмная Сила', 'Дружина Руси', 'Светлая Сказка'));

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Откат: восстановить старые значения (здесь просто комментарий, так как данные были перезаписаны)
-- При необходимости можно переприменить миграцию 20251230110000_add_three_races.sql после отката этой

-- +goose StatementEnd
