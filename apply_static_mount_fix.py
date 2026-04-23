from pathlib import Path

ROOT = Path.cwd()
APP_PATH = ROOT / "src" / "api" / "app.py"

IMPORT_LINE = "from fastapi.staticfiles import StaticFiles"
MOUNT_LINE = 'app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")'

def main() -> None:
    if not APP_PATH.exists():
        raise FileNotFoundError(APP_PATH)

    text = APP_PATH.read_text(encoding="utf-8")

    if IMPORT_LINE not in text:
        marker = "from fastapi.responses import HTMLResponse, JSONResponse, Response"
        if marker not in text:
            raise RuntimeError(f"Could not find import marker: {marker}")
        text = text.replace(
            marker,
            marker + "\n" + IMPORT_LINE,
            1,
        )

    if MOUNT_LINE not in text:
        marker = 'app = FastAPI(title="surveyCatalyst API", version="0.5.0")'
        if marker not in text:
            raise RuntimeError(f"Could not find app marker: {marker}")
        text = text.replace(
            marker,
            marker + "\n" + MOUNT_LINE,
            1,
        )

    APP_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] updated {APP_PATH}")
    print("[DONE] static mount fix applied")

if __name__ == "__main__":
    main()