from __future__ import annotations

from ui.main_window_state import MainWindowState
from ui.map_runtime_service import MapRuntimeService


class RealShellService:
    def __init__(self):
        self.window_state = MainWindowState()
        self.map_runtime = MapRuntimeService()

    def load(self):
        ui_state = self.window_state.load()
        map_state = self.map_runtime.boot()
        return {
            "ui": ui_state,
            "map": map_state,
        }
