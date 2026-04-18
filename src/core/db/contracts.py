from dataclasses import dataclass
from typing import Protocol, Any

@dataclass
class DBConnectionProfile:
    mode: str
    host: str | None = None
    port: int | None = None
    database: str | None = None
    user: str | None = None
    password: str | None = None
    data_dir: str | None = None

class DBBackend(Protocol):
    def connect(self) -> Any: ...
    def healthcheck(self) -> bool: ...
    def close(self) -> None: ...
