from pathlib import Path

APPEND_BLOCK = '''
# === surveyCatalyst UI parcel permission export ===
@app.post("/api/permissions/export")
def export_permission(payload: dict):
    import json
    import re
    from datetime import datetime
    from pathlib import Path

    layer = str(payload.get("layer") or "").strip()
    source_id = str(payload.get("source_id") or "").strip()
    description = str(payload.get("description") or "ui parcel export").strip()

    if not layer or not source_id:
        return {"ok": False, "error": "missing layer or source_id"}

    def _slugify(value: str) -> str:
        raw = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return raw or "permission-export"

    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT layer, source_id, source_table, properties, ST_AsGeoJSON(geom)
                FROM external_features
                WHERE layer = %s AND source_id = %s
                LIMIT 1
                """,
                (layer, source_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return {"ok": False, "error": "feature not found"}

    root = Path.cwd() / "workspace" / "permissions" / "requests"
    root.mkdir(parents=True, exist_ok=True)

    folder = root / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slugify(description)}"
    folder.mkdir(parents=True, exist_ok=True)

    payload_out = {
        "layer": row[0],
        "source_id": row[1],
        "source_table": row[2],
        "properties": row[3],
        "geometry": json.loads(row[4]) if row[4] else None,
        "description": description,
        "saved_at": datetime.now().isoformat(),
    }

    out = folder / "permission_candidate.json"
    out.write_text(json.dumps(payload_out, indent=2), encoding="utf-8")

    return {"ok": True, "folder": str(folder)}
'''

def main():
    root = Path.cwd()

    # --- patch API ---
    app_file = root / "src" / "api" / "app.py"
    text = app_file.read_text(encoding="utf-8")

    if "/api/permissions/export" not in text:
        text += "\\n" + APPEND_BLOCK + "\\n"
        app_file.write_text(text, encoding="utf-8")
        print("[OK] API endpoint added")
    else:
        print("[OK] API endpoint already exists")

    # --- patch UI ---
    html_file = root / "app" / "openlayers_map.html"
    html = html_file.read_text(encoding="utf-8")

    if "exportSelectedParcelBtn" not in html:
        html = html.replace(
            "</body>",
            '''
<button id="exportSelectedParcelBtn" style="position:absolute;bottom:20px;right:20px;z-index:999;">
Export parcel
</button>

<script>
document.getElementById("exportSelectedParcelBtn").onclick = async function() {
    const f = selectInteraction.getFeatures().item(0);
    if (!f) { alert("Select parcel first"); return; }

    const sourceId = f.get("source_id");
    if (!sourceId) { alert("No source_id"); return; }

    const res = await fetch("/api/permissions/export", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            layer: "parcel_boundaries",
            source_id: sourceId,
            description: "ui export"
        })
    });

    const j = await res.json();
    alert(j.ok ? "Export created" : "Failed");
};
</script>
</body>
''',
        )
        html_file.write_text(html, encoding="utf-8")
        print("[OK] UI button added")
    else:
        print("[OK] UI already patched")

    print("[DONE] Restart API and refresh browser")

if __name__ == "__main__":
    main()
