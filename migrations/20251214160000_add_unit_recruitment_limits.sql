-- +goose Up
-- +goose StatementBegin

-- Add recruitment fields to unit_levels table
ALTER TABLE unit_levels ADD COLUMN IF NOT EXISTS daily_recruit_speed INTEGER NOT NULL DEFAULT 1;
ALTER TABLE unit_levels ADD COLUMN IF NOT EXISTS speed_upgrade_cost NUMERIC(12, 2) NOT NULL DEFAULT 100;
ALTER TABLE unit_levels ADD COLUMN IF NOT EXISTS speed_upgrade_cost_gems INTEGER NOT NULL DEFAULT 10;
ALTER TABLE unit_levels ADD COLUMN IF NOT EXISTS level_access_cost_gems INTEGER NOT NULL DEFAULT 0;

-- Set default daily recruit speeds for levels 1 and 2
UPDATE unit_levels SET daily_recruit_speed = 5 WHERE level = 1;
UPDATE unit_levels SET daily_recruit_speed = 2 WHERE level = 2;
UPDATE unit_levels SET daily_recruit_speed = 1 WHERE level >= 3;

-- Set level access costs (only levels 3+ require gems to unlock)
UPDATE unit_levels SET level_access_cost_gems = 0 WHERE level IN (1, 2);
UPDATE unit_levels SET level_access_cost_gems = 50 WHERE level = 3;
UPDATE unit_levels SET level_access_cost_gems = 100 WHERE level = 4;
UPDATE unit_levels SET level_access_cost_gems = 200 WHERE level = 5;
UPDATE unit_levels SET level_access_cost_gems = 500 WHERE level = 6;
UPDATE unit_levels SET level_access_cost_gems = 1000 WHERE level = 7;

-- Create user_unit_limits table for tracking daily recruitment limits
CREATE TABLE IF NOT EXISTS user_unit_limits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES game_users(id) ON DELETE CASCADE,
    unit_level_id INTEGER NOT NULL REFERENCES unit_levels(id) ON DELETE CASCADE,
    available_count INTEGER NOT NULL DEFAULT 0,
    daily_speed INTEGER NOT NULL DEFAULT 1,
    level_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
    last_reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE(user_id, unit_level_id)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_unit_limits_user_id ON user_unit_limits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_unit_limits_level ON user_unit_limits(unit_level_id);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Drop user_unit_limits table
DROP TABLE IF EXISTS user_unit_limits;

-- Remove recruitment fields from unit_levels
ALTER TABLE unit_levels DROP COLUMN IF EXISTS daily_recruit_speed;
ALTER TABLE unit_levels DROP COLUMN IF EXISTS speed_upgrade_cost;
ALTER TABLE unit_levels DROP COLUMN IF EXISTS speed_upgrade_cost_gems;
ALTER TABLE unit_levels DROP COLUMN IF EXISTS level_access_cost_gems;

-- +goose StatementEnd
