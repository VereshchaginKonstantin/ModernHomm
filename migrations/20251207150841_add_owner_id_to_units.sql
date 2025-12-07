-- +goose Up
-- +goose StatementBegin
ALTER TABLE units ADD COLUMN owner_id INTEGER;
ALTER TABLE units ADD CONSTRAINT units_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES game_users(id) ON DELETE CASCADE;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE units DROP CONSTRAINT units_owner_id_fkey;
ALTER TABLE units DROP COLUMN owner_id;
-- +goose StatementEnd
