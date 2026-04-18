from core.db import ConnectionManager

class ManagementService:
    def __init__(self):
        self.cm = ConnectionManager()

    def get_db_status(self):
        rm = self.cm.runtime_manager()
        if not rm:
            return {"mode": "external"}
        s = rm.status()
        return {
            "mode": "local",
            "initialized": s.initialized,
            "running": s.running,
            "binaries": s.binaries_present,
            "port": s.port
        }
