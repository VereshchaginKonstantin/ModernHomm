-- +goose Up
-- +goose StatementBegin

-- Добавляем три новые расы: Тёмная Сила, Дружина Руси, Светлая Сказка

-- =====================================================
-- РАСА 1: ТЁМНАЯ СИЛА (Оборонительная раса)
-- =====================================================
INSERT INTO game_races (name, description, is_free, created_at, updated_at)
VALUES ('Тёмная Сила', 'Оборонительная раса с мощной защитой и ядовитыми атаками', FALSE, NOW(), NOW());

-- Юниты Тёмной Силы
INSERT INTO race_units (
    race_id, unit_level_id, name, is_flying, is_kamikaze, is_big,
    attack, defense, min_damage, max_damage, health, speed, initiative,
    luck, crit_chance, dodge_chance, counterattack_chance, range,
    regeneration_health, poison_damage, poison_turns, poison_immunity, created_at
)
SELECT
    gr.id, ul.id, u.name, u.is_flying, u.is_kamikaze, u.is_big,
    u.attack, u.defense, u.min_damage, u.max_damage, u.health, u.speed, u.initiative,
    u.luck, u.crit_chance, u.dodge_chance, u.counterattack_chance, u.range,
    u.regeneration_health, u.poison_damage, u.poison_turns, u.poison_immunity, NOW()
FROM game_races gr
CROSS JOIN (VALUES
    -- Уровень 1: Кикимора прядущая
    (1, 'Кикимора прядущая', FALSE, FALSE, FALSE, 10, 20, 8, 8, 35, 2, 8, 0.03, 0.04, 0, 0, 1, 4, 0, 0, FALSE),
    -- Уровень 2: Избушка на курьих ножках (БАШНЯ)
    (2, 'Избушка на курьих ножках', FALSE, FALSE, FALSE, 35, 40, 32, 32, 55, 0, 0, 0.02, 0.05, 0, 0, 3, 0, 0, 0, FALSE),
    -- Уровень 3: Леший лесной
    (3, 'Леший лесной', FALSE, FALSE, FALSE, 45, 55, 42, 42, 70, 2, 12, 0.05, 0.08, 0, 0.40, 1, 8, 0, 0, FALSE),
    -- Уровень 4: Баба-Яга в ступе (Летающая, Яд)
    (4, 'Баба-Яга в ступе', TRUE, FALSE, FALSE, 65, 48, 62, 62, 85, 3, 15, 0.10, 0.14, 0, 0, 3, 0, 8, 3, FALSE),
    -- Уровень 5: Соловей-Разбойник (КАМИКАДЗЕ)
    (5, 'Соловей-Разбойник', FALSE, TRUE, FALSE, 3200, 22, 3200, 3200, 45, 3, 18, 0.15, 0.20, 0, 0, 3, 0, 0, 0, FALSE),
    -- Уровень 6: Кощей Бессмертный (Яд, Регенерация)
    (6, 'Кощей Бессмертный', FALSE, FALSE, FALSE, 90, 120, 88, 88, 220, 3, 16, 0.08, 0.12, 0, 0, 2, 30, 16, 5, FALSE),
    -- Уровень 7: Змей Горыныч (Летающий, Контратака, Яд)
    (7, 'Змей Горыныч', TRUE, FALSE, TRUE, 170, 145, 165, 165, 480, 4, 20, 0.14, 0.18, 0, 0.70, 3, 0, 20, 5, FALSE)
) AS u(level, name, is_flying, is_kamikaze, is_big, attack, defense, min_damage, max_damage, health, speed, initiative, luck, crit_chance, dodge_chance, counterattack_chance, range, regeneration_health, poison_damage, poison_turns, poison_immunity)
JOIN unit_levels ul ON ul.level = u.level
WHERE gr.name = 'Тёмная Сила';

-- Создаем скины для юнитов Тёмной Силы
INSERT INTO race_unit_skins (race_unit_id, name, description, created_at)
SELECT ru.id, ru.name || ' (базовый)', 'Базовый скин юнита ' || ru.name, NOW()
FROM race_units ru
JOIN game_races gr ON ru.race_id = gr.id
WHERE gr.name = 'Тёмная Сила';

-- =====================================================
-- РАСА 2: ДРУЖИНА РУСИ (Сбалансированная раса)
-- =====================================================
INSERT INTO game_races (name, description, is_free, created_at, updated_at)
VALUES ('Дружина Руси', 'Сбалансированная раса с хорошими атакой и защитой', TRUE, NOW(), NOW());

-- Юниты Дружины Руси
INSERT INTO race_units (
    race_id, unit_level_id, name, is_flying, is_kamikaze, is_big,
    attack, defense, min_damage, max_damage, health, speed, initiative,
    luck, crit_chance, dodge_chance, counterattack_chance, range,
    regeneration_health, poison_damage, poison_turns, poison_immunity, created_at
)
SELECT
    gr.id, ul.id, u.name, u.is_flying, u.is_kamikaze, u.is_big,
    u.attack, u.defense, u.min_damage, u.max_damage, u.health, u.speed, u.initiative,
    u.luck, u.crit_chance, u.dodge_chance, u.counterattack_chance, u.range,
    u.regeneration_health, u.poison_damage, u.poison_turns, u.poison_immunity, NOW()
FROM game_races gr
CROSS JOIN (VALUES
    -- Уровень 1: Ополченец-смерд
    (1, 'Ополченец-смерд', FALSE, FALSE, FALSE, 22, 16, 20, 20, 28, 2, 9, 0.05, 0.08, 0, 0, 1, 0, 0, 0, FALSE),
    -- Уровень 2: Сторожевая вежа (БАШНЯ)
    (2, 'Сторожевая вежа', FALSE, FALSE, FALSE, 38, 45, 35, 35, 60, 0, 0, 0.03, 0.07, 0, 0, 3, 0, 0, 0, FALSE),
    -- Уровень 3: Стрелец московский (Дальнобойный, Крит)
    (3, 'Стрелец московский', FALSE, FALSE, FALSE, 60, 28, 58, 58, 38, 2, 11, 0.12, 0.16, 0, 0, 4, 0, 0, 0, FALSE),
    -- Уровень 4: Волхв-ведун (Яд, Регенерация)
    (4, 'Волхв-ведун', FALSE, FALSE, FALSE, 50, 68, 46, 46, 105, 2, 13, 0.12, 0.10, 0, 0, 3, 14, 10, 4, FALSE),
    -- Уровень 5: Опричник царский (Контратака, Крит)
    (5, 'Опричник царский', FALSE, FALSE, FALSE, 100, 65, 98, 98, 115, 4, 17, 0.13, 0.20, 0, 0.60, 1, 0, 0, 0, FALSE),
    -- Уровень 6: Порохонос-смертник (КАМИКАДЗЕ)
    (6, 'Порохонос-смертник', FALSE, TRUE, FALSE, 3100, 18, 3100, 3100, 42, 3, 16, 0.10, 0.15, 0, 0, 2, 0, 0, 0, FALSE),
    -- Уровень 7: Князь на крылатом коне (Летающий, Контратака)
    (7, 'Князь на крылатом коне', TRUE, FALSE, TRUE, 160, 105, 155, 155, 330, 5, 22, 0.16, 0.22, 0, 0.65, 2, 0, 0, 0, FALSE)
) AS u(level, name, is_flying, is_kamikaze, is_big, attack, defense, min_damage, max_damage, health, speed, initiative, luck, crit_chance, dodge_chance, counterattack_chance, range, regeneration_health, poison_damage, poison_turns, poison_immunity)
JOIN unit_levels ul ON ul.level = u.level
WHERE gr.name = 'Дружина Руси';

-- Создаем скины для юнитов Дружины Руси
INSERT INTO race_unit_skins (race_unit_id, name, description, created_at)
SELECT ru.id, ru.name || ' (базовый)', 'Базовый скин юнита ' || ru.name, NOW()
FROM race_units ru
JOIN game_races gr ON ru.race_id = gr.id
WHERE gr.name = 'Дружина Руси';

-- =====================================================
-- РАСА 3: СВЕТЛАЯ СКАЗКА (Атакующая раса)
-- =====================================================
INSERT INTO game_races (name, description, is_free, created_at, updated_at)
VALUES ('Светлая Сказка', 'Атакующая раса с высоким уроном и критами', FALSE, NOW(), NOW());

-- Юниты Светлой Сказки
INSERT INTO race_units (
    race_id, unit_level_id, name, is_flying, is_kamikaze, is_big,
    attack, defense, min_damage, max_damage, health, speed, initiative,
    luck, crit_chance, dodge_chance, counterattack_chance, range,
    regeneration_health, poison_damage, poison_turns, poison_immunity, created_at
)
SELECT
    gr.id, ul.id, u.name, u.is_flying, u.is_kamikaze, u.is_big,
    u.attack, u.defense, u.min_damage, u.max_damage, u.health, u.speed, u.initiative,
    u.luck, u.crit_chance, u.dodge_chance, u.counterattack_chance, u.range,
    u.regeneration_health, u.poison_damage, u.poison_turns, u.poison_immunity, NOW()
FROM game_races gr
CROSS JOIN (VALUES
    -- Уровень 1: Домовой-хранитель (Регенерация)
    (1, 'Домовой-хранитель', FALSE, FALSE, FALSE, 12, 20, 11, 11, 26, 2, 10, 0.06, 0.07, 0, 0, 1, 6, 0, 0, FALSE),
    -- Уровень 2: Золотой терем (БАШНЯ)
    (2, 'Золотой терем', FALSE, FALSE, FALSE, 40, 48, 38, 38, 65, 0, 0, 0.05, 0.08, 0, 0, 3, 0, 0, 0, FALSE),
    -- Уровень 3: Серый Волк (Быстрый, Крит)
    (3, 'Серый Волк', FALSE, FALSE, FALSE, 68, 36, 64, 64, 50, 5, 16, 0.11, 0.17, 0, 0, 1, 0, 0, 0, FALSE),
    -- Уровень 4: Царевна-Лебедь (Летающая, Регенерация)
    (4, 'Царевна-Лебедь', TRUE, FALSE, FALSE, 58, 45, 55, 55, 72, 4, 17, 0.13, 0.16, 0, 0, 3, 14, 0, 0, FALSE),
    -- Уровень 5: Богатырь Илья Муромец (Контратака, Крит)
    (5, 'Богатырь Илья Муромец', FALSE, FALSE, FALSE, 118, 88, 115, 115, 175, 3, 15, 0.15, 0.19, 0, 0.65, 1, 0, 0, 0, FALSE),
    -- Уровень 6: Жар-птица (Летающая, Огонь - как яд, Крит)
    (6, 'Жар-птица', TRUE, FALSE, FALSE, 130, 68, 125, 125, 132, 5, 20, 0.18, 0.22, 0, 0, 3, 0, 13, 4, FALSE),
    -- Уровень 7: Иван-царевич на Коньке-Горбунке (КАМИКАДЗЕ - героическое самопожертвование)
    (7, 'Иван-царевич на Коньке-Горбунке', FALSE, TRUE, TRUE, 4500, 48, 4500, 4500, 100, 5, 24, 0.20, 0.28, 0, 0, 2, 0, 0, 0, FALSE)
) AS u(level, name, is_flying, is_kamikaze, is_big, attack, defense, min_damage, max_damage, health, speed, initiative, luck, crit_chance, dodge_chance, counterattack_chance, range, regeneration_health, poison_damage, poison_turns, poison_immunity)
JOIN unit_levels ul ON ul.level = u.level
WHERE gr.name = 'Светлая Сказка';

-- Создаем скины для юнитов Светлой Сказки
INSERT INTO race_unit_skins (race_unit_id, name, description, created_at)
SELECT ru.id, ru.name || ' (базовый)', 'Базовый скин юнита ' || ru.name, NOW()
FROM race_units ru
JOIN game_races gr ON ru.race_id = gr.id
WHERE gr.name = 'Светлая Сказка';

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Удаляем скины
DELETE FROM race_unit_skins WHERE race_unit_id IN (
    SELECT ru.id FROM race_units ru
    JOIN game_races gr ON ru.race_id = gr.id
    WHERE gr.name IN ('Тёмная Сила', 'Дружина Руси', 'Светлая Сказка')
);

-- Удаляем юнитов рас
DELETE FROM race_units WHERE race_id IN (
    SELECT id FROM game_races WHERE name IN ('Тёмная Сила', 'Дружина Руси', 'Светлая Сказка')
);

-- Удаляем расы
DELETE FROM game_races WHERE name IN ('Тёмная Сила', 'Дружина Руси', 'Светлая Сказка');

-- +goose StatementEnd
