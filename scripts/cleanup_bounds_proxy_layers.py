from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend


def main() -> int:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM external_features
                WHERE COALESCE(properties->>'source','') = 'osm_overpass_relation_bounds_proxy'
                   OR COALESCE(properties->>'bounds_proxy','') IN ('true', 'True', '1')
                """
            )
            ext_deleted = cur.rowcount

            deleted = {}
            for table in ("bkg_vg250_boundaries", "bkg_vg25_boundaries"):
                cur.execute(
                    f"""
                    DELETE FROM data_layers.{table}
                    WHERE COALESCE(properties->>'source','') = 'osm_overpass_relation_bounds_proxy'
                       OR COALESCE(properties->>'bounds_proxy','') IN ('true', 'True', '1')
                    """
                )
                deleted[table] = cur.rowcount

        conn.commit()
    finally:
        conn.close()

    print(
        "[DONE] removed bounds-proxy features "
        f"external_features={ext_deleted} "
        + " ".join(f"{k}={v}" for k, v in deleted.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
