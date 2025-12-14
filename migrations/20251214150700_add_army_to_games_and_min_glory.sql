-- +goose Up
-- +goose StatementBegin

-- Add army columns to games table
ALTER TABLE games ADD COLUMN IF NOT EXISTS player1_army_id INTEGER REFERENCES armies(id) ON DELETE SET NULL;
ALTER TABLE games ADD COLUMN IF NOT EXISTS player2_army_id INTEGER REFERENCES armies(id) ON DELETE SET NULL;

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_games_player1_army ON games(player1_army_id);
CREATE INDEX IF NOT EXISTS idx_games_player2_army ON games(player2_army_id);

-- Set minimum glory to 500 for users with 0 or NULL glory
UPDATE game_users SET glory = 500 WHERE glory IS NULL OR glory = 0;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Remove indexes
DROP INDEX IF EXISTS idx_games_player1_army;
DROP INDEX IF EXISTS idx_games_player2_army;

-- Remove army columns from games
ALTER TABLE games DROP COLUMN IF EXISTS player1_army_id;
ALTER TABLE games DROP COLUMN IF EXISTS player2_army_id;

-- Note: Cannot rollback glory update as we don't know original values

-- +goose StatementEnd
