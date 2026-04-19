import json
from pathlib import Path
from core.config.settings import Settings


CONFIG_PATH = Path("config/app_config.json")


def load_settings() -> Settings:
    if not CONFIG_PATH.exists():
        raise RuntimeError("Missing config/app_config.json")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Settings.from_dict(data)
