from __future__ import annotations


class IngestionRegistry:
    def list_sources(self):
        return [
            "itiner-e",
            "viabundus",
            "blfd",
            "gesis",
        ]
