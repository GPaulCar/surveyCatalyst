from dataclasses import dataclass
from pathlib import Path
import socket

@dataclass
class LocalPostgresRuntimeStatus:
    postgres_root: Path
    data_dir: Path
    bin_dir: Path
    share_dir: Path
    port: int
    initialized: bool
    binaries_present: bool
    running: bool

class RuntimeManager:
    def __init__(self, postgres_root: Path, port: int):
        self.postgres_root = postgres_root
        self.data_dir = postgres_root / 'data'
        self.bin_dir = postgres_root / 'bin'
        self.share_dir = postgres_root / 'share'
        self.port = port

    def ensure_layout(self):
        for p in [self.postgres_root, self.data_dir, self.bin_dir, self.share_dir]:
            p.mkdir(parents=True, exist_ok=True)

    def is_running(self):
        s = socket.socket()
        try:
            return s.connect_ex(('127.0.0.1', self.port)) == 0
        finally:
            s.close()
