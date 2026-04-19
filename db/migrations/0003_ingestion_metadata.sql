CREATE TABLE IF NOT EXISTS ingestion_sources (
    id SERIAL PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    provider_class TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    default_schema_name TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id SERIAL PRIMARY KEY,
    source_key TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'running',
    message TEXT,
    records_loaded INTEGER,
    layer_keys JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS ingestion_artifacts (
    id SERIAL PRIMARY KEY,
    source_key TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    local_path TEXT NOT NULL,
    remote_url TEXT,
    version_label TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO ingestion_sources (source_key, source_name, provider_class, default_schema_name, notes)
VALUES
    ('itiner_e', 'Itiner-e Roman Roads', 'ItinerEProvider', 'ancient', 'Roman roads and routes'),
    ('viabundus', 'Viabundus Transport Network', 'ViabundusProvider', 'medieval', 'Premodern nodes and edges'),
    ('blfd', 'BLfD Restricted Areas', 'BLfDProvider', 'legal', 'Protected and restricted areas'),
    ('gesis', 'GESIS Bavaria Economy', 'GESISProvider', 'economic', 'Historical Bavaria economy and mining')
ON CONFLICT (source_key) DO NOTHING;
