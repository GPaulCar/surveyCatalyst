from __future__ import annotations

from dataclasses import dataclass
import time
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
        last_error: Exception | None = None
        for attempt in range(30):
            try:
                self._conn = psycopg.connect(self.dsn(), connect_timeout=2)
                return self._conn
            except Exception as exc:
                last_error = exc
                if attempt == 29:
                    break
                time.sleep(1.0)
        if last_error is not None:
            raise last_error
        raise RuntimeError("database connection failed")

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
