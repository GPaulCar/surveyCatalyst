from __future__ import annotations


class TabShellService:
    TAB_ORDER = ["Layers", "Details", "Survey", "Data"]

    def get_tabs(self):
        return list(self.TAB_ORDER)

    def build_shell_state(self, window_state):
        loaded = window_state.load()
        return {
            "tabs": self.get_tabs(),
            "layers": loaded["layers"],
            "surveys": loaded["surveys"],
            "details": loaded["details"],
        }
