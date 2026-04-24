from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()

BOOT = ROOT / "app" / "static" / "ui_boot.js"

def update_ui_labels():
    text = BOOT.read_text(encoding="utf-8")

    if "TEXT_LABEL_STYLE" in text:
        print("[INFO] label styling already present")
        return

    inject = """
const TEXT_LABEL_STYLE = function(feature, color){
  const name = feature.get("name") || feature.get("title") || feature.get("place") || "";
  if (!name) return null;

  return new ol.style.Style({
    text: new ol.style.Text({
      text: name,
      font: "12px sans-serif",
      fill: new ol.style.Fill({color: color || "#111"}),
      stroke: new ol.style.Stroke({color:"#ffffff", width:3}),
      offsetY: -12
    })
  });
};
"""

    text = text.replace("let contextTileLayers = {};", "let contextTileLayers = {};\n" + inject)

    # inject into style function
    text = text.replace(
        "if (gt.includes(\"POINT\")) {",
        """
if (gt.includes("POINT")) {
  const label = TEXT_LABEL_STYLE(feature, "#111");
  if (label) return label;
"""
    )

    BOOT.write_text(text, encoding="utf-8")
    print("[OK] UI label styling applied")


def run(cmd):
    print(f"[RUN] {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"[FAIL] {cmd}")
        sys.exit(result.returncode)


def verify_counts():
    print("[INFO] verifying layer counts")
    result = subprocess.run(
        [sys.executable, "scripts/layer_counts.py"],
        capture_output=True,
        text=True
    )
    print(result.stdout)

    required = [
        "old_creeks",
        "old_channels",
        "wetland_history",
        "field_names",
        "geonames_points",
    ]

    missing = []
    for r in required:
        if r not in result.stdout:
            missing.append(r)

    if missing:
        print(f"[FAIL] missing layers: {missing}")
        sys.exit(1)

    print("[OK] counts present")


def main():
    print("[1/6] updating UI for labels")
    update_ui_labels()

    print("[2/6] build layers")
    run(f"{sys.executable} scripts/build_historical_enrichment_layers.py")

    print("[3/6] ingest data")
    run(f"{sys.executable} scripts/ingest_historical_enrichment_osm.py")

    print("[4/6] verify counts")
    verify_counts()

    print("[5/6] restart system")
    run(f"{sys.executable} scripts/system_control.py restart")

    print("[6/6] checkpoint")
    run(f"{sys.executable} apply_checkpoint_bundle.py historical-enrichment-stage1 --no-push")

    print("\n[PHASE COMPLETE]")
    print("historical + enrichment active")
    print("labels enabled for point layers")


if __name__ == "__main__":
    main()