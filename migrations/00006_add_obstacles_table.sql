-- +goose Up
-- +goose StatementBegin
CREATE TABLE obstacles (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    position_x INTEGER NOT NULL CHECK (position_x >= 0),
    position_y INTEGER NOT NULL CHECK (position_y >= 0)
);

CREATE INDEX idx_obstacles_game_id ON obstacles(game_id);

COMMENT ON TABLE obstacles IS 'Препятствия на игровом поле';
COMMENT ON COLUMN obstacles.game_id IS 'ID игры, к которой относится препятствие';
COMMENT ON COLUMN obstacles.position_x IS 'Координата X препятствия на поле';
COMMENT ON COLUMN obstacles.position_y IS 'Координата Y препятствия на поле';
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE IF EXISTS obstacles;
-- +goose StatementEnd
