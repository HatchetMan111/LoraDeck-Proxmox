from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _decode_hash(value: str) -> str:
    if not value.startswith("b64:"):
        return value
    raw = value[4:]
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding).decode("utf-8")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    db_path: Path
    static_dir: Path
    secret: str
    admin_user: str
    admin_hash: str
    session_ttl: int = 43200
    cookie_secure: bool = False
    gateway_url: str = ""
    gateway_auth: str = ""
    poll_interval: int = 60
    poll_enabled: bool = True
    backup_dir: Path = Path("/var/lib/loradeck/backups")
    gateway_timeout: float = 8.0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=Path(
                os.environ.get("LORADECK_DB", "/var/lib/loradeck/loradeck.db")
            ),
            static_dir=Path(
                os.environ.get(
                    "LORADECK_STATIC", str(PACKAGE_ROOT / "web" / "dist")
                )
            ),
            secret=os.environ.get("LORADECK_SECRET", ""),
            admin_user=os.environ.get("LORADECK_ADMIN_USER", "admin"),
            admin_hash=_decode_hash(os.environ.get("LORADECK_ADMIN_HASH", "")),
            session_ttl=_int_env("LORADECK_SESSION_TTL", 43200),
            cookie_secure=os.environ.get("LORADECK_COOKIE_SECURE", "0") == "1",
            gateway_url=os.environ.get("LORADECK_GATEWAY_URL", "").strip(),
            gateway_auth=os.environ.get("LORADECK_GATEWAY_AUTH", "").strip(),
            poll_interval=_int_env("LORADECK_POLL_INTERVAL", 60),
            poll_enabled=os.environ.get("LORADECK_POLL_ENABLED", "1") == "1",
            backup_dir=Path(
                os.environ.get(
                    "LORADECK_BACKUP_DIR", "/var/lib/loradeck/backups"
                )
            ),
            gateway_timeout=_float_env("LORADECK_GATEWAY_TIMEOUT", 8.0),
        )
