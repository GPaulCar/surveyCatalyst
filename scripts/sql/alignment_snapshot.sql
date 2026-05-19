WITH
idn AS (
  SELECT current_database()::text AS db,
         inet_server_addr()::text AS host,
         inet_server_port()::int AS port,
         now() AS ts
),
ext AS (
  SELECT jsonb_agg(jsonb_build_object('ext', extname, 'ver', extversion) ORDER BY extname) AS v
  FROM pg_extension
),
bkg_registry AS (
  SELECT jsonb_agg(
           jsonb_build_object(
             'layer_key', layer_key,
             'is_visible', is_visible,
             'is_user_selectable', is_user_selectable,
             'source_table', source_table,
             'metadata', metadata
           )
           ORDER BY layer_key
         ) AS v
  FROM layers_registry
  WHERE layer_key IN ('bkg_vg250_boundaries','bkg_vg25_boundaries')
),
bkg_rows AS (
  SELECT jsonb_agg(jsonb_build_object('layer', layer, 'rows', cnt) ORDER BY layer) AS v
  FROM (
    SELECT 'bkg_vg25'::text AS layer, COUNT(*)::bigint AS cnt FROM data_layers.bkg_vg25_boundaries
    UNION ALL
    SELECT 'bkg_vg250'::text, COUNT(*)::bigint FROM data_layers.bkg_vg250_boundaries
  ) s
),
bkg_proxy AS (
  SELECT jsonb_agg(jsonb_build_object('layer', layer, 'proxy_rows', cnt) ORDER BY layer) AS v
  FROM (
    SELECT 'bkg_vg25'::text AS layer,
           COUNT(*)::bigint AS cnt
    FROM data_layers.bkg_vg25_boundaries
    WHERE COALESCE(properties->>'bounds_proxy','') <> ''
       OR COALESCE(properties->>'source','') = 'osm_overpass_relation_bounds_proxy'
    UNION ALL
    SELECT 'bkg_vg250'::text,
           COUNT(*)::bigint
    FROM data_layers.bkg_vg250_boundaries
    WHERE COALESCE(properties->>'bounds_proxy','') <> ''
       OR COALESCE(properties->>'source','') = 'osm_overpass_relation_bounds_proxy'
  ) s
),
layer_counts AS (
  SELECT jsonb_agg(jsonb_build_object('layer', layer, 'count', cnt) ORDER BY layer) AS v
  FROM (
    SELECT layer, COUNT(*)::bigint AS cnt
    FROM external_features
    GROUP BY layer
  ) s
),
settings AS (
  SELECT jsonb_agg(
           jsonb_build_object('name', name, 'setting', setting, 'unit', unit, 'context', context)
           ORDER BY name
         ) AS v
  FROM pg_settings
  WHERE name IN (
    'shared_buffers','effective_cache_size','work_mem','maintenance_work_mem',
    'random_page_cost','seq_page_cost','effective_io_concurrency','max_parallel_workers',
    'max_parallel_workers_per_gather','max_worker_processes','max_wal_size','min_wal_size',
    'checkpoint_timeout','autovacuum','autovacuum_max_workers','autovacuum_naptime',
    'autovacuum_vacuum_scale_factor','autovacuum_analyze_scale_factor'
  )
)
SELECT jsonb_pretty(
  jsonb_build_object(
    'identity', (SELECT to_jsonb(idn) FROM idn),
    'extensions', COALESCE((SELECT v FROM ext), '[]'::jsonb),
    'bkg_registry', COALESCE((SELECT v FROM bkg_registry), '[]'::jsonb),
    'bkg_row_counts', COALESCE((SELECT v FROM bkg_rows), '[]'::jsonb),
    'bkg_proxy_rows', COALESCE((SELECT v FROM bkg_proxy), '[]'::jsonb),
    'external_feature_layer_counts', COALESCE((SELECT v FROM layer_counts), '[]'::jsonb),
    'key_pg_settings', COALESCE((SELECT v FROM settings), '[]'::jsonb)
  )
) AS alignment_snapshot;
