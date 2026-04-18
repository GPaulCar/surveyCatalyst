from __future__ import annotations

from core.db.connection_manager import ConnectionManager
from core.db.postgres_backend import PostgresBackend


def build_backend():
    profile = ConnectionManager().active_profile()
    return PostgresBackend(profile)
