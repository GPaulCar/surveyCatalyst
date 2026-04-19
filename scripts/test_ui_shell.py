import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.main_window_state import MainWindowState
from ui.tab_shell_service import TabShellService

state = MainWindowState()
shell = TabShellService()

result = shell.build_shell_state(state)

print("TABS:", result["tabs"])
print("LAYERS:", result["layers"])
print("SURVEYS:", result["surveys"])
print("DETAILS:", result["details"])
