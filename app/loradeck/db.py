from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gateway_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    online INTEGER NOT NULL,
    fw TEXT NOT NULL DEFAULT '',
    hw TEXT NOT NULL DEFAULT '',
    uptime INTEGER,
    heap INTEGER,
    ip TEXT NOT NULL DEFAULT '',
    ssid TEXT NOT NULL DEFAULT '',
    rssi INTEGER,
    mode TEXT NOT NULL DEFAULT '',
    ns_ready INTEGER,
    devices INTEGER,
    error TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_samples_ts ON gateway_samples(ts DESC, id DESC);
CREATE TABLE IF NOT EXISTS sensors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dev_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    grp TEXT NOT NULL DEFAULT '',
    decoder TEXT NOT NULL DEFAULT '',
    cls TEXT NOT NULL DEFAULT '',
    fcnt INTEGER,
    status TEXT NOT NULL DEFAULT '',
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC, id DESC);
CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    filename TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    size INTEGER NOT NULL,
    sha256 TEXT NOT NULL
);
"""


class ConflictError(Exception):
    """Raised when a unique value is already in use."""


class NotFoundError(Exception):
    """Raised when a row does not exist."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


# --------------------------------------------------------------- settings


def ensure_settings(conn: sqlite3.Connection, defaults: dict[str, str]) -> None:
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
    conn.commit()


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row is not None else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    conn.commit()


# ------------------------------------------------------------------ state


def get_state(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row is not None else default


def set_state(
    conn: sqlite3.Connection, key: str, value: str, now: str | None = None
) -> None:
    conn.execute(
        """
        INSERT INTO state (key, value, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE
            SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, value, now or utc_now()),
    )
    conn.commit()


# ---------------------------------------------------------------- samples


def record_sample(conn: sqlite3.Connection, sample: dict[str, Any]) -> int:
    cur = conn.execute(
        """
        INSERT INTO gateway_samples
            (ts, online, fw, hw, uptime, heap, ip, ssid, rssi, mode,
             ns_ready, devices, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sample.get("ts") or utc_now(),
            1 if sample.get("online") else 0,
            str(sample.get("fw") or ""),
            str(sample.get("hw") or ""),
            sample.get("uptime"),
            sample.get("heap"),
            str(sample.get("ip") or ""),
            str(sample.get("ssid") or ""),
            sample.get("rssi"),
            str(sample.get("mode") or ""),
            sample.get("ns_ready"),
            sample.get("devices"),
            str(sample.get("error") or ""),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def _sample_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["online"] = bool(item.get("online"))
    if item.get("ns_ready") is not None:
        item["ns_ready"] = bool(item["ns_ready"])
    return item


def latest_sample(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM gateway_samples ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return _sample_row(row) if row is not None else None


def recent_samples(
    conn: sqlite3.Connection, limit: int = 120
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM gateway_samples ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [_sample_row(row) for row in reversed(rows)]


# ---------------------------------------------------------------- sensors


def _sensor_row(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def list_sensors(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM sensors ORDER BY name COLLATE NOCASE, dev_id"
    ).fetchall()
    return [_sensor_row(row) for row in rows]


def upsert_sensors(
    conn: sqlite3.Connection,
    devices: Iterable[dict[str, Any]],
    now: str | None = None,
) -> list[dict[str, str]]:
    now = now or utc_now()
    changes: list[dict[str, str]] = []
    for device in devices:
        dev_id = str(device.get("dev_id") or "").strip()
        if not dev_id:
            continue
        name = str(device.get("name") or "")
        grp = str(device.get("grp") or "")
        decoder = str(device.get("decoder") or "")
        cls = str(device.get("cls") or "")
        status = str(device.get("status") or "")
        fcnt = device.get("fcnt")
        row = conn.execute(
            "SELECT * FROM sensors WHERE dev_id = ?", (dev_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO sensors
                    (dev_id, name, grp, decoder, cls, fcnt, status,
                     first_seen, last_seen, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (dev_id, name, grp, decoder, cls, fcnt, status, now, now, now),
            )
            changes.append(
                {
                    "kind": "sensor_new",
                    "message": f"Neuer Sensor: {name or dev_id}",
                }
            )
            continue
        old_status = str(row["status"] or "")
        conn.execute(
            """
            UPDATE sensors
               SET name = ?, grp = ?, decoder = ?, cls = ?, fcnt = ?,
                   status = ?, last_seen = ?, updated_at = ?
             WHERE dev_id = ?
            """,
            (name, grp, decoder, cls, fcnt, status, now, now, dev_id),
        )
        if status != old_status:
            changes.append(
                {
                    "kind": "sensor_status",
                    "message": (
                        f"{name or dev_id}: Status {old_status or '—'} → "
                        f"{status or '—'}"
                    ),
                }
            )
    conn.commit()
    return changes


# ----------------------------------------------------------------- events


def add_event(
    conn: sqlite3.Connection,
    kind: str,
    message: str,
    now: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO events (ts, kind, message) VALUES (?, ?, ?)",
        (now or utc_now(), kind, message),
    )
    conn.commit()


def list_events(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(row) for row in rows]


def prune_events(conn: sqlite3.Connection, keep: int = 5000) -> None:
    conn.execute(
        """
        DELETE FROM events
         WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT ?)
        """,
        (keep,),
    )
    conn.commit()


# ---------------------------------------------------------------- backups


def _backup_row(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def add_backup(
    conn: sqlite3.Connection,
    *,
    ts: str,
    filename: str,
    kind: str,
    size: int,
    sha256: str,
) -> dict[str, Any]:
    try:
        cur = conn.execute(
            """
            INSERT INTO backups (ts, filename, kind, size, sha256)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts, filename, kind, size, sha256),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ConflictError(f"backup '{filename}' already exists") from exc
    item = get_backup(conn, int(cur.lastrowid))
    assert item is not None
    return item


def list_backups(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM backups ORDER BY id DESC"
    ).fetchall()
    return [_backup_row(row) for row in rows]


def get_backup(conn: sqlite3.Connection, backup_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM backups WHERE id = ?", (backup_id,)
    ).fetchone()
    return _backup_row(row) if row is not None else None


def delete_backup(conn: sqlite3.Connection, backup_id: int) -> dict[str, Any]:
    item = get_backup(conn, backup_id)
    if item is None:
        raise NotFoundError(f"backup {backup_id} not found")
    conn.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
    conn.commit()
    return item


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    sensors = conn.execute("SELECT COUNT(*) AS n FROM sensors").fetchone()
    events = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()
    backups = conn.execute("SELECT COUNT(*) AS n FROM backups").fetchone()
    return {
        "sensors": int(sensors["n"]),
        "events": int(events["n"]),
        "backups": int(backups["n"]),
    }
