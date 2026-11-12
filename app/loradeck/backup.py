from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__, db
from .config import Settings
from .gateway import GatewayClient

logger = logging.getLogger("loradeck.backup")


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def create_backup(
    conn, settings: Settings, client: GatewayClient
) -> dict[str, Any]:
    config = client.export_config(secrets=False)
    lns = client.export_lns()
    ts = db.utc_now()
    document = {
        "backup": {
            "tool": "loradeck",
            "version": __version__,
            "date": ts,
            "source": client.base_url,
            "config_secrets": False,
        },
        "config": config,
        "lns": lns,
    }
    payload = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    filename = f"loradeck-backup-{_timestamp_slug()}-{secrets.token_hex(2)}.json"
    path = settings.backup_dir / filename
    tmp = path.with_suffix(".tmp")
    with open(tmp, "wb") as handle:
        handle.write(payload)
    tmp.replace(path)
    path.chmod(0o600)
    return db.add_backup(
        conn,
        ts=ts,
        filename=filename,
        kind="config+lns",
        size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def backup_path(settings: Settings, item: dict[str, Any]) -> Path | None:
    name = str(item.get("filename") or "")
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    root = settings.backup_dir.resolve()
    candidate = (root / name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def delete_backup(conn, settings: Settings, backup_id: int) -> None:
    item = db.get_backup(conn, backup_id)
    if item is None:
        raise db.NotFoundError(f"backup {backup_id} not found")
    path = backup_path(settings, item)
    if path is not None:
        try:
            path.unlink()
        except OSError:
            logger.warning("Backup-Datei konnte nicht gelöscht werden: %s", path)
    db.delete_backup(conn, backup_id)
