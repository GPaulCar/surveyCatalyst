from __future__ import annotations


class SelectionContract:
    def __init__(self):
        self._selected = None
        self._listeners = []

    def subscribe(self, callback):
        self._listeners.append(callback)

    def select(self, item_type: str, item_id: int, payload=None):
        self._selected = {
            "item_type": item_type,
            "item_id": item_id,
            "payload": payload,
        }
        for callback in self._listeners:
            callback(self._selected)

    def current(self):
        return self._selected
