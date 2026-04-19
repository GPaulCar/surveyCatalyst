from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AppSettings:
    name: str
    env: str


@dataclass
class DBLocalSettings:
    data_dir: str
    port: int
    database: str
    user: str


@dataclass
class DBExternalSettings:
    host: str
    port: int
    database: str
    user: str


@dataclass
class DBSettings:
    mode: str
    local: DBLocalSettings
    external: DBExternalSettings


@dataclass
class PathSettings:
    assets: str
    logs: str


@dataclass
class Settings:
    app: AppSettings
    db: DBSettings
    paths: PathSettings

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Settings":
        return Settings(
            app=AppSettings(**data["app"]),
            db=DBSettings(
                mode=data["db"]["mode"],
                local=DBLocalSettings(**data["db"]["local"]),
                external=DBExternalSettings(**data["db"]["external"]),
            ),
            paths=PathSettings(**data["paths"]),
        )
