import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.real_shell_service import RealShellService

shell = RealShellService()
state = shell.load()
print("STATE:", state)

print("TOGGLE survey_objects ON")
print(shell.map_runtime.toggle_layer("survey_objects", True))

print("TOGGLE survey_objects OFF")
print(shell.map_runtime.toggle_layer("survey_objects", False))
