-- +goose Up
-- +goose StatementBegin
ALTER TABLE obstacles ADD COLUMN IF NOT EXISTS width INTEGER NOT NULL DEFAULT 1;
ALTER TABLE obstacles ADD COLUMN IF NOT EXISTS height INTEGER NOT NULL DEFAULT 1;

-- Add constraints
ALTER TABLE obstacles ADD CONSTRAINT obstacle_positive_width CHECK (width >= 1);
ALTER TABLE obstacles ADD CONSTRAINT obstacle_positive_height CHECK (height >= 1);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE obstacles DROP CONSTRAINT IF EXISTS obstacle_positive_height;
ALTER TABLE obstacles DROP CONSTRAINT IF EXISTS obstacle_positive_width;
ALTER TABLE obstacles DROP COLUMN IF EXISTS height;
ALTER TABLE obstacles DROP COLUMN IF EXISTS width;
-- +goose StatementEnd
