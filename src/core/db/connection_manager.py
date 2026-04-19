from pathlib import Path
from core.config import load_settings
from core.db.contracts import DBConnectionProfile
from core.db.runtime_manager import RuntimeManager


class ConnectionManager:
    def active_profile(self) -> DBConnectionProfile:
        s = load_settings()

        if s.db.mode == "local":
            return DBConnectionProfile(
                mode="local",
                host="127.0.0.1",
                port=s.db.local.port,
                database=s.db.local.database,
                user=s.db.local.user,
                data_dir=s.db.local.data_dir,
            )

        return DBConnectionProfile(
            mode="external",
            host=s.db.external.host,
            port=s.db.external.port,
            database=s.db.external.database,
            user=s.db.external.user,
        )

    def runtime_manager(self):
        p = self.active_profile()
        if p.mode != "local" or not p.data_dir:
            return None
        return RuntimeManager(Path(p.data_dir).resolve().parent, p.port or 5432)