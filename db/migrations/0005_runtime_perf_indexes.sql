CREATE INDEX IF NOT EXISTS idx_external_features_layer_geom_gist
ON external_features
USING GIST (geom)
WHERE geom IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_external_features_layer_btree
ON external_features (layer);

CREATE INDEX IF NOT EXISTS idx_external_features_layer_source_id
ON external_features (layer, source_id);

CREATE INDEX IF NOT EXISTS idx_survey_objects_layer_active
ON survey_objects (layer_key, is_active);

CREATE INDEX IF NOT EXISTS idx_survey_objects_survey_active
ON survey_objects (survey_id, is_active);

CREATE INDEX IF NOT EXISTS idx_surveys_layer_key
ON surveys (layer_key);
