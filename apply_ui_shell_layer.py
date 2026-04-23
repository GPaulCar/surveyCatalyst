from pathlib import Path
import json

ROOT = Path.cwd()

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[OK] {path}")

def main():
    # --- 1. SHELL HTML ---
    shell_html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>SurveyCatalyst</title>

  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@latest/ol.css">

  <style>
    html, body { margin:0; padding:0; height:100%; }
    #map { position:absolute; inset:0; }

    #ui-root {
      position:absolute;
      inset:0;
      pointer-events:none;
      font-family: Arial, sans-serif;
    }

    .panel {
      pointer-events:auto;
      position:absolute;
      top:20px;
      bottom:20px;
      background:#1e1f23;
      color:white;
      border-radius:12px;
      padding:10px;
      overflow:auto;
    }

    #left-panel { left:20px; width:360px; }
    #right-panel { right:20px; width:420px; }

    .selection-banner {
      position:absolute;
      top:10px;
      left:50%;
      transform:translateX(-50%);
      background:orange;
      padding:10px 20px;
      border-radius:8px;
      color:black;
      pointer-events:auto;
    }
  </style>
</head>

<body>
  <div id="map"></div>

  <div id="ui-root">
    <div id="left-panel" class="panel"></div>
    <div id="right-panel" class="panel"></div>
    <div id="selection-banner" class="selection-banner" style="display:none;"></div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/ol@latest/dist/ol.js"></script>
  <script src="/static/ui_boot.js"></script>
</body>
</html>
"""

    # --- 2. UI MANIFEST ---
    manifest = {
        "left_tabs": [
            {"id": "manage", "title": "Manage"},
            {"id": "create", "title": "Create"},
            {"id": "edit", "title": "Edit"},
            {"id": "export", "title": "Export"}
        ],
        "right_tabs": [
            {"id": "hierarchy", "title": "Hierarchy"},
            {"id": "details", "title": "Details"},
            {"id": "layers", "title": "Layers"}
        ]
    }

    # --- 3. UI BOOT ---
    ui_boot = """// UI BOOT LAYER

async function loadManifest() {
  const res = await fetch('/static/ui_manifest.json');
  return res.json();
}

// --- GLOBAL SELECTION ---
window.activeSelection = null;

function setSelection(text) {
  const banner = document.getElementById('selection-banner');
  banner.innerText = text;
  banner.style.display = 'block';
}

// --- MAP INIT ---
const map = new ol.Map({
  target: 'map',
  layers: [
    new ol.layer.Tile({
      source: new ol.source.OSM()
    })
  ],
  view: new ol.View({
    center: ol.proj.fromLonLat([11,48]),
    zoom: 7
  })
});

// --- UI BUILD ---
async function initUI() {
  const manifest = await loadManifest();

  const left = document.getElementById('left-panel');
  const right = document.getElementById('right-panel');

  left.innerHTML = manifest.left_tabs.map(t => 
    `<div><b>${t.title}</b></div>`
  ).join('');

  right.innerHTML = manifest.right_tabs.map(t => 
    `<div><b>${t.title}</b></div>`
  ).join('');
}

initUI();
"""

    # --- WRITE FILES ---
    write(ROOT / "app/openlayers_map_shell.html", shell_html)
    write(ROOT / "app/static/ui_boot.js", ui_boot)
    write(ROOT / "app/static/ui_manifest.json", json.dumps(manifest, indent=2))

    print("\\n[DONE] UI shell layer created")
    print("Next: switch API to serve openlayers_map_shell.html")

if __name__ == "__main__":
    main()