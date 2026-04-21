from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app" / "live_db_map_app.py"

subprocess.run([sys.executable, "-m", "streamlit", "run", str(APP)], check=True)
