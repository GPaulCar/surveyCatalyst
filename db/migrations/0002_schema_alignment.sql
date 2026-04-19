CREATE TABLE IF NOT EXISTS layers_registry (
    id SERIAL PRIMARY KEY,
    layer_key TEXT NOT NULL UNIQUE,
    layer_name TEXT NOT NULL,
    layer_group TEXT NOT NULL CHECK (layer_group IN ('base', 'context', 'survey')),
    source_table TEXT,
    geometry_type TEXT,
    is_user_selectable BOOLEAN NOT NULL DEFAULT TRUE,
    is_visible BOOLEAN NOT NULL DEFAULT TRUE,
    opacity DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE surveys
    ADD COLUMN IF NOT EXISTS layer_key TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE survey_objects
    ADD COLUMN IF NOT EXISTS layer_key TEXT,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE external_features
    ADD COLUMN IF NOT EXISTS source_table TEXT,
    ADD COLUMN IF NOT EXISTS source_id TEXT;

CREATE INDEX IF NOT EXISTS idx_layers_registry_group_sort
    ON layers_registry(layer_group, sort_order);

CREATE INDEX IF NOT EXISTS idx_survey_objects_layer_key
    ON survey_objects(layer_key);

CREATE INDEX IF NOT EXISTS idx_external_features_layer
    ON external_features(layer, source_table);

INSERT INTO layers_registry (layer_key, layer_name, layer_group, source_table, geometry_type, is_user_selectable, is_visible, opacity, sort_order)
VALUES
    ('surveys', 'Surveys', 'survey', 'surveys', 'POLYGON', TRUE, TRUE, 1.0, 10),
    ('survey_objects', 'Survey Objects', 'survey', 'survey_objects', 'GEOMETRY', TRUE, TRUE, 1.0, 20)
ON CONFLICT (layer_key) DO NOTHING;
