from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()
HTML_PATH = ROOT / "app" / "openlayers_map.html"
API_PATH = ROOT / "src" / "api" / "app.py"

UI2_CSS_START = "  body, html { overflow: hidden; }"
UI2_CSS_END = "  #scratchNoteBtn { width: auto; margin: 0; padding: 10px 14px; }\n"

UI2_JS_START = "let allowCrossSurveySelection = false;"
UI2_JS_END = "}\n\nfunction bindTabs() {"

API_APPEND_START = "# === ui2 scratch notes and selection support ==="
API_APPEND_END = '    return {"ok": True, "id": row[0]}\n'

def remove_block(text: str, start_marker: str, end_marker: str, keep_end: bool = False) -> str:
    start = text.find(start_marker)
    if start == -1:
        return text
    end = text.find(end_marker, start)
    if end == -1:
        return text
    if keep_end:
        return text[:start] + text[end:]
    return text[:start] + text[end + len(end_marker):]

def repair_html() -> None:
    text = HTML_PATH.read_text(encoding="utf-8")

    text = remove_block(text, UI2_CSS_START, UI2_CSS_END)
    text = remove_block(text, UI2_JS_START, UI2_JS_END, keep_end=True)

    text = text.replace("ensureAppShell();\n", "")
    text = text.replace("\nensureAppShell();", "\n")
    text = text.replace("  setGlobalSelection(feature);", "")
    text = text.replace('  appShell.insertAdjacentHTML(\'beforeend\', `__SELECTION_BANNER_HTML__`);\n', "")
    text = text.replace(SELECTION_BANNER_HTML_LITERAL(), "")

    HTML_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] repaired {HTML_PATH}")

def SELECTION_BANNER_HTML_LITERAL() -> str:
    return """
  <div id="selectionBanner" class="selectionBanner hidden">
    <span id="selectionBannerText">No selection</span>
    <button id="clearSelectionBtn" type="button">Clear</button>
  </div>
"""

def repair_api() -> None:
    text = API_PATH.read_text(encoding="utf-8")
    text = remove_block(text, API_APPEND_START, API_APPEND_END)
    API_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] repaired {API_PATH}")

def main() -> None:
    if not HTML_PATH.exists():
        raise FileNotFoundError(HTML_PATH)
    if not API_PATH.exists():
        raise FileNotFoundError(API_PATH)

    repair_html()
    repair_api()

    print("[DONE] UI-1 / UI-2 injection removed")
    print("Restart the API and hard refresh the browser.")

if __name__ == "__main__":
    main()