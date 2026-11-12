from __future__ import annotations

import threading

import pytest

from loradeck import db


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(tmp_path / "test.db")
    db.init_db(connection)
    yield connection
    connection.close()


def test_connection_usable_across_threads(conn):
    result = {}

    def worker():
        result["value"] = db.get_setting(conn, "missing", "fallback")

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert result["value"] == "fallback"


def test_settings_roundtrip(conn):
    db.ensure_settings(
        conn, {"gateway_url": "http://192.168.1.40", "poll_interval": "60"}
    )
    assert db.get_setting(conn, "gateway_url") == "http://192.168.1.40"
    assert db.get_setting(conn, "poll_interval") == "60"
    assert db.get_setting(conn, "missing", "fallback") == "fallback"
    db.set_setting(conn, "gateway_url", "http://192.168.1.41")
    assert db.get_setting(conn, "gateway_url") == "http://192.168.1.41"


def test_state_roundtrip(conn):
    assert db.get_state(conn, "last_online", "unknown") == "unknown"
    db.set_state(conn, "last_online", "1")
    assert db.get_state(conn, "last_online") == "1"


def test_samples_order_and_latest(conn):
    for index in range(3):
        db.record_sample(
            conn,
            {
                "ts": f"2026-11-12T10:0{index}:00+00:00",
                "online": True,
                "fw": "3.4.2",
                "rssi": -60 - index,
                "devices": 3,
            },
        )
    samples = db.recent_samples(conn, 10)
    assert [item["rssi"] for item in samples] == [-60, -61, -62]
    latest = db.latest_sample(conn)
    assert latest is not None
    assert latest["rssi"] == -62
    assert latest["online"] is True


def test_offline_sample(conn):
    db.record_sample(
        conn,
        {"ts": "2026-11-12T10:00:00+00:00", "online": False, "error": "Timeout"},
    )
    latest = db.latest_sample(conn)
    assert latest is not None
    assert latest["online"] is False
    assert latest["error"] == "Timeout"


def test_upsert_sensors_new_and_status_change(conn):
    changes = db.upsert_sensors(
        conn,
        [
            {
                "dev_id": "A1",
                "name": "Werkstatt",
                "grp": "A",
                "decoder": "LHT52",
                "cls": "A",
                "fcnt": 1,
                "status": "active",
            }
        ],
        now="2026-11-12T10:00:00+00:00",
    )
    assert changes == [
        {"kind": "sensor_new", "message": "Neuer Sensor: Werkstatt"}
    ]
    sensors = db.list_sensors(conn)
    assert len(sensors) == 1
    assert sensors[0]["first_seen"] == "2026-11-12T10:00:00+00:00"

    changes = db.upsert_sensors(
        conn,
        [
            {
                "dev_id": "A1",
                "name": "Werkstatt",
                "grp": "A",
                "decoder": "LHT52",
                "cls": "A",
                "fcnt": 2,
                "status": "inactive",
            }
        ],
        now="2026-11-12T11:00:00+00:00",
    )
    assert changes == [
        {
            "kind": "sensor_status",
            "message": "Werkstatt: Status active → inactive",
        }
    ]
    sensors = db.list_sensors(conn)
    assert sensors[0]["fcnt"] == 2
    assert sensors[0]["first_seen"] == "2026-11-12T10:00:00+00:00"
    assert sensors[0]["last_seen"] == "2026-11-12T11:00:00+00:00"


def test_upsert_sensors_skips_missing_id(conn):
    changes = db.upsert_sensors(conn, [{"name": "ohne ID"}])
    assert changes == []
    assert db.list_sensors(conn) == []


def test_events_and_prune(conn):
    for index in range(5):
        db.add_event(conn, "test", f"event {index}", f"2026-11-12T10:0{index}:00+00:00")
    events = db.list_events(conn, 10)
    assert [item["message"] for item in events] == [
        "event 4",
        "event 3",
        "event 2",
        "event 1",
        "event 0",
    ]
    db.prune_events(conn, keep=2)
    events = db.list_events(conn, 10)
    assert len(events) == 2
    assert events[0]["message"] == "event 4"


def test_backups_crud(conn, tmp_path):
    item = db.add_backup(
        conn,
        ts="2026-11-12T10:00:00+00:00",
        filename="loradeck-backup-test.json",
        kind="config+lns",
        size=42,
        sha256="abc",
    )
    assert item["id"] == 1
    assert db.list_backups(conn)[0]["filename"] == "loradeck-backup-test.json"
    assert db.get_backup(conn, 1) is not None
    with pytest.raises(db.ConflictError):
        db.add_backup(
            conn,
            ts="2026-11-12T10:01:00+00:00",
            filename="loradeck-backup-test.json",
            kind="config+lns",
            size=42,
            sha256="abc",
        )
    db.delete_backup(conn, 1)
    assert db.get_backup(conn, 1) is None
    with pytest.raises(db.NotFoundError):
        db.delete_backup(conn, 1)


def test_counts(conn):
    db.add_event(conn, "test", "one")
    assert db.counts(conn) == {"sensors": 0, "events": 1, "backups": 0}
