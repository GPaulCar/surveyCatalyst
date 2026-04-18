from pathlib import Path
from core.config import load_settings
from core.db.contracts import DBConnectionProfile
from core.db.runtime_manager import RuntimeManager

class ConnectionManager:
    def active_profile(self):
        s = load_settings()
        if s.db.mode == 'local':
            return DBConnectionProfile(mode='local', port=s.db.local.port, data_dir=s.db.local.data_dir)
        return DBConnectionProfile(mode='external')

    def runtime_manager(self):
        p = self.active_profile()
        if p.mode != 'local': return None
        return RuntimeManager(Path(p.data_dir).parent, p.port)
