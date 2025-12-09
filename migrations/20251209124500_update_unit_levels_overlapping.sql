-- +goose Up
-- Обновление диапазонов параметров юнитов с пересечениями между уровнями
-- Уровень 7 теперь достигает: стоимость 1000, защита 100, урон 100

UPDATE unit_levels SET
    min_damage = 1, max_damage = 5,
    min_defense = 1, max_defense = 3,
    min_health = 5, max_health = 25,
    min_speed = 1, max_speed = 3,
    min_cost = 10, max_cost = 50
WHERE level = 1;

UPDATE unit_levels SET
    min_damage = 3, max_damage = 10,
    min_defense = 2, max_defense = 8,
    min_health = 15, max_health = 50,
    min_speed = 2, max_speed = 4,
    min_cost = 30, max_cost = 100
WHERE level = 2;

UPDATE unit_levels SET
    min_damage = 6, max_damage = 18,
    min_defense = 5, max_defense = 15,
    min_health = 30, max_health = 90,
    min_speed = 2, max_speed = 5,
    min_cost = 70, max_cost = 180
WHERE level = 3;

UPDATE unit_levels SET
    min_damage = 12, max_damage = 30,
    min_defense = 10, max_defense = 28,
    min_health = 60, max_health = 160,
    min_speed = 3, max_speed = 6,
    min_cost = 140, max_cost = 320
WHERE level = 4;

UPDATE unit_levels SET
    min_damage = 22, max_damage = 50,
    min_defense = 20, max_defense = 45,
    min_health = 120, max_health = 280,
    min_speed = 3, max_speed = 7,
    min_cost = 260, max_cost = 500
WHERE level = 5;

UPDATE unit_levels SET
    min_damage = 38, max_damage = 75,
    min_defense = 35, max_defense = 70,
    min_health = 200, max_health = 450,
    min_speed = 4, max_speed = 8,
    min_cost = 420, max_cost = 750
WHERE level = 6;

UPDATE unit_levels SET
    min_damage = 55, max_damage = 100,
    min_defense = 55, max_defense = 100,
    min_health = 350, max_health = 700,
    min_speed = 5, max_speed = 10,
    min_cost = 650, max_cost = 1000
WHERE level = 7;

-- +goose Down
-- Восстановление оригинальных значений

UPDATE unit_levels SET
    min_damage = 1, max_damage = 3,
    min_defense = 1, max_defense = 2,
    min_health = 5, max_health = 15,
    min_speed = 1, max_speed = 2,
    min_cost = 10, max_cost = 30
WHERE level = 1;

UPDATE unit_levels SET
    min_damage = 2, max_damage = 5,
    min_defense = 2, max_defense = 4,
    min_health = 10, max_health = 25,
    min_speed = 2, max_speed = 3,
    min_cost = 25, max_cost = 60
WHERE level = 2;

UPDATE unit_levels SET
    min_damage = 4, max_damage = 8,
    min_defense = 3, max_defense = 6,
    min_health = 20, max_health = 40,
    min_speed = 2, max_speed = 4,
    min_cost = 50, max_cost = 100
WHERE level = 3;

UPDATE unit_levels SET
    min_damage = 6, max_damage = 12,
    min_defense = 5, max_defense = 9,
    min_health = 35, max_health = 60,
    min_speed = 3, max_speed = 5,
    min_cost = 80, max_cost = 150
WHERE level = 4;

UPDATE unit_levels SET
    min_damage = 10, max_damage = 18,
    min_defense = 7, max_defense = 12,
    min_health = 50, max_health = 90,
    min_speed = 3, max_speed = 6,
    min_cost = 120, max_cost = 220
WHERE level = 5;

UPDATE unit_levels SET
    min_damage = 15, max_damage = 25,
    min_defense = 10, max_defense = 16,
    min_health = 70, max_health = 130,
    min_speed = 4, max_speed = 7,
    min_cost = 180, max_cost = 320
WHERE level = 6;

UPDATE unit_levels SET
    min_damage = 20, max_damage = 35,
    min_defense = 14, max_defense = 22,
    min_health = 100, max_health = 200,
    min_speed = 5, max_speed = 8,
    min_cost = 280, max_cost = 500
WHERE level = 7;
