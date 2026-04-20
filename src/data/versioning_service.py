from datetime import datetime, timezone


class VersioningService:
    def generate_version(self, source_key: str):
        return f"{source_key}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
