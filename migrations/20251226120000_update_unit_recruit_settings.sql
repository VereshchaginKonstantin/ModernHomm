-- +goose Up
-- +goose StatementBegin

-- Update daily recruit speeds according to requirements:
-- Level 1: 2 units/day
-- Level 2: 1 unit/day
-- Levels 3+: 0 units/day (requires unlock)
UPDATE unit_levels SET daily_recruit_speed = 2 WHERE level = 1;
UPDATE unit_levels SET daily_recruit_speed = 1 WHERE level = 2;
UPDATE unit_levels SET daily_recruit_speed = 0 WHERE level >= 3;

-- Ensure levels 1 and 2 have 0 unlock cost (should already be set, but ensure)
UPDATE unit_levels SET level_access_cost_gems = 0 WHERE level IN (1, 2);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Revert to previous settings
UPDATE unit_levels SET daily_recruit_speed = 5 WHERE level = 1;
UPDATE unit_levels SET daily_recruit_speed = 2 WHERE level = 2;
UPDATE unit_levels SET daily_recruit_speed = 1 WHERE level >= 3;

-- +goose StatementEnd
