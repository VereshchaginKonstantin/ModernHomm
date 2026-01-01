-- +goose Up
-- +goose StatementBegin

-- Добавляем поля для предустановленных шаблонов полей челленджей
ALTER TABLE challenges ADD COLUMN IF NOT EXISTS field_template_5x5_id INTEGER REFERENCES battle_field_templates(id) ON DELETE SET NULL;
ALTER TABLE challenges ADD COLUMN IF NOT EXISTS field_template_7x7_id INTEGER REFERENCES battle_field_templates(id) ON DELETE SET NULL;
ALTER TABLE challenges ADD COLUMN IF NOT EXISTS field_template_10x10_id INTEGER REFERENCES battle_field_templates(id) ON DELETE SET NULL;

-- Индексы для ускорения поиска
CREATE INDEX IF NOT EXISTS idx_challenges_field_template_5x5 ON challenges(field_template_5x5_id) WHERE field_template_5x5_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_challenges_field_template_7x7 ON challenges(field_template_7x7_id) WHERE field_template_7x7_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_challenges_field_template_10x10 ON challenges(field_template_10x10_id) WHERE field_template_10x10_id IS NOT NULL;

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

DROP INDEX IF EXISTS idx_challenges_field_template_5x5;
DROP INDEX IF EXISTS idx_challenges_field_template_7x7;
DROP INDEX IF EXISTS idx_challenges_field_template_10x10;

ALTER TABLE challenges DROP COLUMN IF EXISTS field_template_5x5_id;
ALTER TABLE challenges DROP COLUMN IF EXISTS field_template_7x7_id;
ALTER TABLE challenges DROP COLUMN IF EXISTS field_template_10x10_id;

-- +goose StatementEnd
