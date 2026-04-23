from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd()

WORKSPACE_LAYOUT = {
    "workspace": "",
    "workspace/downloads": "",
    "workspace/downloads/raw": "",
    "workspace/downloads/raw/osm": "",
    "workspace/downloads/curated": "",
    "workspace/downloads/curated/itinere": "",
    "workspace/exports": "",
}

STORAGE_PATHS_PY = """from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT / "workspace"
DOWNLOADS_ROOT = WORKSPACE_ROOT / "downloads"
DOWNLOADS_RAW_ROOT = DOWNLOADS_ROOT / "raw"
DOWNLOADS_CURATED_ROOT = DOWNLOADS_ROOT / "curated"
EXPORTS_ROOT = WORKSPACE_ROOT / "exports"

for path in [
    WORKSPACE_ROOT,
    DOWNLOADS_ROOT,
    DOWNLOADS_RAW_ROOT,
    DOWNLOADS_CURATED_ROOT,
    EXPORTS_ROOT,
]:
    path.mkdir(parents=True, exist_ok=True)

def slugify(value: str | None, default: str = "export") -> str:
    raw = (value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or default

def timestamp_slug(description: str | None, default: str = "export") -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{slugify(description, default=default)}"

def export_folder(description: str | None, default: str = "export") -> Path:
    folder = EXPORTS_ROOT / timestamp_slug(description, default=default)
    folder.mkdir(parents=True, exist_ok=True)
    return folder
"""

APPEND_APP_PY = """

# === surveyCatalyst storage/export extension ===
def _sc_storage_root():
    from pathlib import Path
    root = Path.cwd() / "workspace"
    (root / "downloads" / "raw" / "osm").mkdir(parents=True, exist_ok=True)
    (root / "downloads" / "curated" / "itinere").mkdir(parents=True, exist_ok=True)
    (root / "exports").mkdir(parents=True, exist_ok=True)
    return root

def _sc_slugify(value: str | None, default: str = "export") -> str:
    import re
    raw = (value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or default

@app.get("/api/storage/summary")
def sc_storage_summary():
    root = _sc_storage_root()
    return {
        "workspace": str(root),
        "downloads_raw": str(root / "downloads" / "raw"),
        "downloads_curated": str(root / "downloads" / "curated"),
        "exports": str(root / "exports"),
    }

@app.post("/api/exports/save")
def sc_save_export(payload: dict):
    import base64
    from datetime import datetime
    from pathlib import Path

    root = _sc_storage_root()
    description = payload.get("description") or "export"
    kind = payload.get("kind") or "export"
    filename = payload.get("filename") or f"{kind}.bin"
    content_b64 = payload.get("content_base64") or ""
    survey_id = payload.get("survey_id")
    folder_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_sc_slugify(description, default='export')}"
    folder = root / "exports" / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    target = folder / filename
    target.write_bytes(base64.b64decode(content_b64))

    meta = {
        "description": description,
        "kind": kind,
        "filename": filename,
        "mime_type": payload.get("mime_type"),
        "survey_id": survey_id,
        "saved_at": datetime.now().isoformat(),
        "path": str(target),
    }
    (folder / "export_meta.json").write_text(__import__("json").dumps(meta, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "folder": str(folder),
        "path": str(target),
        "filename": filename,
    }
"""

HELPER_JS = """
function slugifyText(value, fallback='export') {
  const slug = String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || fallback;
}

function currentExportDescription() {
  const input = document.getElementById('exportDescription');
  return input ? input.value.trim() : '';
}

function utf8ToBase64(text) {
  const bytes = new TextEncoder().encode(text);
  const chunkSize = 0x8000;
  let binary = '';
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

async function saveServerExport(kind, filename, content, mimeType) {
  const res = await fetch('/api/exports/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      kind,
      description: currentExportDescription() || `survey-${activeSurveyId || 'export'}-${kind}`,
      filename,
      mime_type: mimeType,
      survey_id: activeSurveyId,
      content_base64: utf8ToBase64(content)
    })
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Failed to save export on server');
  }
  return await res.json();
}
"""

NEW_DOWNLOAD_LAYER = """async function downloadLayerExport() {
  if (!activeSurveyId) { setStatus('Select an active survey first.'); return; }
  try {
    const opts = getExportOptions();
    const query = buildQuery({
      include_boundary: opts.include_boundary,
      include_objects: opts.include_objects,
      include_archived: opts.include_archived
    });
    const payload = await fetchJson(`/api/surveys/${activeSurveyId}/export/layer.geojson?${query}`);
    const descriptionSlug = slugifyText(currentExportDescription(), `survey-${activeSurveyId}-layer`);
    const filename = `survey_${activeSurveyId}_${descriptionSlug}_layer.geojson`;
    const content = JSON.stringify(payload, null, 2);
    const saved = await saveServerExport('layer', filename, content, 'application/geo+json');
    downloadText(filename, content, 'application/geo+json');
    setStatus(`Downloaded layer export and saved server copy in ${saved.folder}.`, 'success');
  } catch (error) {
    setStatus(`Layer export failed: ${error.message}`, 'error');
  }
}"""

NEW_DOWNLOAD_DATA = """async function downloadDataExport() {
  if (!activeSurveyId) { setStatus('Select an active survey first.'); return; }
  try {
    const opts = getExportOptions();
    const query = buildQuery({
      include_boundary: opts.include_boundary,
      include_objects: opts.include_objects,
      include_archived: opts.include_archived,
      include_geometry: opts.include_geometry,
      include_properties: opts.include_properties
    });
    const payload = await fetchJson(`/api/surveys/${activeSurveyId}/export/data.json?${query}`);
    const descriptionSlug = slugifyText(currentExportDescription(), `survey-${activeSurveyId}-data`);
    const filename = `survey_${activeSurveyId}_${descriptionSlug}_data.json`;
    const content = JSON.stringify(payload, null, 2);
    const saved = await saveServerExport('data', filename, content, 'application/json');
    downloadText(filename, content, 'application/json');
    setStatus(`Downloaded data export and saved server copy in ${saved.folder}.`, 'success');
  } catch (error) {
    setStatus(`Data export failed: ${error.message}`, 'error');
  }
}"""

NEW_DOWNLOAD_DOC = """async function downloadDocumentExport() {
  if (!activeSurveyId) { setStatus('Select an active survey first.'); return; }
  try {
    const opts = getExportOptions();
    const query = buildQuery({
      include_boundary: opts.include_boundary,
      include_objects: opts.include_objects,
      include_archived: opts.include_archived,
      include_geometry: false,
      include_properties: opts.include_properties
    });
    const payload = await fetchJson(`/api/surveys/${activeSurveyId}/export/document.json?${query}`);
    const mapImage = opts.include_document_map ? getCurrentMapImageDataUrl() : null;
    const html = buildPrintableDocumentHtml(payload, mapImage, opts.include_document_details);
    const descriptionSlug = slugifyText(currentExportDescription(), `survey-${activeSurveyId}-document`);
    const filename = `survey_${activeSurveyId}_${descriptionSlug}_document.html`;
    const saved = await saveServerExport('document', filename, html, 'text/html');
    downloadText(filename, html, 'text/html');
    setStatus(`Downloaded printable document and saved server copy in ${saved.folder}.`, 'success');
  } catch (error) {
    setStatus(`Document export failed: ${error.message}`, 'error');
  }
}"""

CURATED_REPLACEMENT = """OUTPUT_DIR = ROOT / "workspace" / "downloads" / "curated" / "itinere"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)"""

OSM_EXTRA = """
RAW_OUTPUT_DIR = ROOT / "workspace" / "downloads" / "raw" / "osm"
RAW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
"""

OSM_FETCH_REPLACEMENT = """def fetch_overpass() -> dict:
    from datetime import datetime
    data = urllib.parse.urlencode({"data": QUERY}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "surveyCatalyst/phase2-dual-roman-roads"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = RAW_OUTPUT_DIR / f"roman_roads_osm_{stamp}.json"
    raw_file.write_text(json.dumps(payload), encoding="utf-8")
    return payload"""

def patch_app_py(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "/api/exports/save" not in text:
        text += APPEND_APP_PY
    path.write_text(text, encoding="utf-8")

def patch_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if 'id="exportDescription"' not in text:
        target = """      <div class="buttonGridCompact">
        <button id="downloadLayerExportBtn">GeoJSON</button>
        <button id="downloadDataExportBtn">Data JSON</button>
        <button id="downloadDocumentExportBtn" class="fullWidth">Document</button>
      </div>"""
        replacement = """      <label for="exportDescription">Export description</label>
      <input id="exportDescription" type="text" placeholder="brief label for folder name">
      <div class="small">Exports are downloaded locally and also saved under workspace/exports/&lt;timestamp&gt;_&lt;description&gt;/.</div>
      <div class="buttonGridCompact">
        <button id="downloadLayerExportBtn">GeoJSON</button>
        <button id="downloadDataExportBtn">Data JSON</button>
        <button id="downloadDocumentExportBtn" class="fullWidth">Document</button>
      </div>"""
        if target in text:
            text = text.replace(target, replacement, 1)
    if "function saveServerExport(" not in text:
        marker = "async function downloadLayerExport() {"
        text = text.replace(marker, HELPER_JS + "\n\n" + marker, 1)

    text = re.sub(r"async function downloadLayerExport\(\) \{.*?\n\}", NEW_DOWNLOAD_LAYER, text, count=1, flags=re.S)
    text = re.sub(r"async function downloadDataExport\(\) \{.*?\n\}", NEW_DOWNLOAD_DATA, text, count=1, flags=re.S)
    text = re.sub(r"async function downloadDocumentExport\(\) \{.*?\n\}", NEW_DOWNLOAD_DOC, text, count=1, flags=re.S)

    path.write_text(text, encoding="utf-8")

def patch_curated_script(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'OUTPUT_DIR = ROOT .*?\nOUTPUT_DIR\.mkdir\(parents=True, exist_ok=True\)', CURATED_REPLACEMENT, text, count=1, flags=re.S)
    text = re.sub(r'out_path = OUTPUT_DIR / "itinere_roads\.geojson"', 'from datetime import datetime\n    out_path = OUTPUT_DIR / f"itinere_roads_{datetime.now().strftime(\'%Y%m%d_%H%M%S\')}.geojson"', text, count=1)
    path.write_text(text, encoding="utf-8")

def patch_osm_script(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if "RAW_OUTPUT_DIR" not in text:
        marker = 'LAYER_KEY = "roman_roads_osm"\n'
        text = text.replace(marker, marker + OSM_EXTRA + "\n", 1)
    text = re.sub(r"def fetch_overpass\(\) -> dict:.*?return json\.loads\(resp\.read\(\)\.decode\(\"utf-8\"\)\)\n", OSM_FETCH_REPLACEMENT + "\n", text, count=1, flags=re.S)
    path.write_text(text, encoding="utf-8")

def write_storage_paths(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(STORAGE_PATHS_PY, encoding="utf-8")

def ensure_workspace() -> None:
    for rel in WORKSPACE_LAYOUT:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

def main() -> None:
    ensure_workspace()

    app_py = ROOT / "src" / "api" / "app.py"
    html = ROOT / "app" / "openlayers_map.html"
    curated = ROOT / "scripts" / "ingest_roman_roads_curated_itinere.py"
    osm = ROOT / "scripts" / "ingest_roman_roads_osm.py"
    storage_paths = ROOT / "scripts" / "storage_paths.py"

    if not app_py.exists():
      raise FileNotFoundError(app_py)
    if not html.exists():
      raise FileNotFoundError(html)

    patch_app_py(app_py)
    print(f"[OK] rewrote {app_py}")

    patch_html(html)
    print(f"[OK] rewrote {html}")

    patch_curated_script(curated)
    if curated.exists():
        print(f"[OK] rewrote {curated}")

    patch_osm_script(osm)
    if osm.exists():
        print(f"[OK] rewrote {osm}")

    write_storage_paths(storage_paths)
    print(f"[OK] wrote {storage_paths}")

    print("[DONE] storage/download/export organisation applied")
    print("Workspace folders:")
    print(f"  {ROOT / 'workspace' / 'downloads' / 'raw'}")
    print(f"  {ROOT / 'workspace' / 'downloads' / 'curated'}")
    print(f"  {ROOT / 'workspace' / 'exports'}")

if __name__ == "__main__":
    main()
