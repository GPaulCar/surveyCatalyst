from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg

from core.db.contracts import DBBackend, DBConnectionProfile


@dataclass
class PostgresBackend(DBBackend):
    profile: DBConnectionProfile
    _conn: Any = None

    def dsn(self) -> str:
        parts = []
        if self.profile.host:
            parts.append(f"host={self.profile.host}")
        if self.profile.port:
            parts.append(f"port={self.profile.port}")
        if self.profile.database:
            parts.append(f"dbname={self.profile.database}")
        if self.profile.user:
            parts.append(f"user={self.profile.user}")
        if self.profile.password:
            parts.append(f"password={self.profile.password}")
        return " ".join(parts)

    def connect(self):
        self._conn = psycopg.connect(self.dsn())
        return self._conn

    def healthcheck(self) -> bool:
        try:
            conn = self._conn or self.connect()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
            return bool(row and row[0] == 1)
        except Exception:
            return False

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
