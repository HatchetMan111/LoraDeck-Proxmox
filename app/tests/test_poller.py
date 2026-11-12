from __future__ import annotations

import copy

import pytest

from loradeck import db
from loradeck.gateway import GatewayError
from loradeck.poller import poll_once

from .fixtures import LNS, STATUS


class FakeClient:
    def __init__(self, status=None, lns=None, error: str = "") -> None:
        self.status_payload = copy.deepcopy(status or STATUS)
        self.lns_payload = copy.deepcopy(lns or LNS)
        self.error = error
        self.closed = False

    def status(self):
        if self.error:
            raise GatewayError(self.error)
        return self.status_payload

    def lns(self):
        if self.error:
            raise GatewayError(self.error)
        return self.lns_payload

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(tmp_path / "poller.db")
    db.init_db(connection)
    yield connection
    connection.close()


def test_poll_once_records_status_sensors_and_events(conn, settings):
    result = poll_once(conn, settings, FakeClient())
    assert result["ok"] is True
    assert result["devices"] == 3

    sample = db.latest_sample(conn)
    assert sample is not None
    assert sample["online"] is True
    assert sample["fw"] == "3.4.2"
    assert sample["rssi"] == -67
    assert sample["devices"] == 3
    assert sample["ns_ready"] is True

    sensors = db.list_sensors(conn)
    assert len(sensors) == 3
    assert {item["name"] for item in sensors} == {
        "Werkstatt",
        "Rauchmelder",
        "Tor",
    }

    events = db.list_events(conn)
    kinds = [item["kind"] for item in events]
    assert "online" in kinds
    assert kinds.count("sensor_new") == 3
    assert db.get_state(conn, "last_online") == "1"
    assert db.get_state(conn, "last_fw") == "3.4.2"


def test_second_poll_does_not_repeat_online_event(conn, settings):
    poll_once(conn, settings, FakeClient())
    first = len(db.list_events(conn, 100))
    poll_once(conn, settings, FakeClient())
    second = len(db.list_events(conn, 100))
    assert second == first


def test_offline_transition_is_recorded_once(conn, settings):
    poll_once(conn, settings, FakeClient())
    result = poll_once(conn, settings, FakeClient(error="Timeout"))
    assert result["ok"] is False
    sample = db.latest_sample(conn)
    assert sample is not None
    assert sample["online"] is False
    assert sample["error"] == "Timeout"
    assert db.get_state(conn, "last_online") == "0"
    assert db.get_state(conn, "last_error") == "Timeout"

    poll_once(conn, settings, FakeClient(error="Timeout"))
    offline_events = [
        item for item in db.list_events(conn, 100) if item["kind"] == "offline"
    ]
    assert len(offline_events) == 1


def test_firmware_change_event(conn, settings):
    poll_once(conn, settings, FakeClient())
    updated = copy.deepcopy(STATUS)
    updated["sys"]["fw"] = "3.4.3"
    poll_once(conn, settings, FakeClient(status=updated))
    firmware_events = [
        item for item in db.list_events(conn, 100) if item["kind"] == "firmware"
    ]
    assert len(firmware_events) == 1
    assert "3.4.2" in firmware_events[0]["message"]
    assert "3.4.3" in firmware_events[0]["message"]


def test_device_count_falls_back_to_lns_list(conn, settings):
    status = copy.deepcopy(STATUS)
    del status["lns"]["devices"]
    poll_once(conn, settings, FakeClient(status=status))
    sample = db.latest_sample(conn)
    assert sample is not None
    assert sample["devices"] == 3
