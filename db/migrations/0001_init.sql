CREATE TABLE IF NOT EXISTS surveys (
    id SERIAL PRIMARY KEY,
    expedition_id INTEGER,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    geom geometry(POLYGON, 4326),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS survey_objects (
    id SERIAL PRIMARY KEY,
    survey_id INTEGER REFERENCES surveys(id) ON DELETE CASCADE,
    expedition_id INTEGER,
    type TEXT NOT NULL,
    geom geometry(GEOMETRY, 4326),
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS external_features (
    id SERIAL PRIMARY KEY,
    layer TEXT,
    geom geometry(GEOMETRY, 4326),
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_surveys_geom
    ON surveys USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_survey_objects_geom
    ON survey_objects USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_external_features_geom
    ON external_features USING GIST (geom);
