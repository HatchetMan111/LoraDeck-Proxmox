from __future__ import annotations

import httpx
import pytest

from loradeck.gateway import (
    GatewayClient,
    GatewayError,
    normalize_base_url,
    normalize_devices,
    normalize_status,
)

from .fixtures import FIRMWARE, LNS, STATUS


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/status":
        return httpx.Response(200, json=STATUS)
    if request.url.path == "/lns/api":
        return httpx.Response(200, json=LNS)
    if request.url.path == "/fw":
        return httpx.Response(200, json=FIRMWARE)
    return httpx.Response(404)


def _client(handler=_handler, **kwargs) -> GatewayClient:
    return GatewayClient(
        "http://gateway.test",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def test_status_and_lns():
    with _client() as client:
        assert client.status()["sys"]["fw"] == "3.4.2"
        assert len(client.lns()["devices"]) == 3


def test_basic_auth_header():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization", "")
        return httpx.Response(200, json=STATUS)

    with _client(handler, auth="monitor:secret") as client:
        client.status()
    assert seen["auth"].startswith("Basic ")


def test_unauthorized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401)

    with _client(handler) as client:
        with pytest.raises(GatewayError, match="401"):
            client.status()


def test_server_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with _client(handler) as client:
        with pytest.raises(GatewayError, match="HTTP 500"):
            client.status()


def test_non_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    with _client(handler) as client:
        with pytest.raises(GatewayError, match="nicht mit JSON"):
            client.status()


def test_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with _client(handler) as client:
        with pytest.raises(GatewayError, match="nicht erreichbar"):
            client.status()


def test_check_firmware_waits_for_checked_change():
    state = {"checked": FIRMWARE["checked"], "checks": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/fw" and request.url.params.get("action") == "check":
            state["checks"] += 1
            state["checked"] += 1
            return httpx.Response(200, json={"ok": True})
        firmware = dict(FIRMWARE)
        firmware["checked"] = state["checked"]
        firmware["avail"] = "3.4.3" if state["checks"] else ""
        return httpx.Response(200, json=firmware)

    with _client(handler) as client:
        result = client.check_firmware(attempts=1, delay=0)
    assert state["checks"] == 1
    assert result["avail"] == "3.4.3"


def test_normalize_status_missing_fields():
    result = normalize_status({})
    assert result["fw"] == ""
    assert result["uptime"] is None
    assert result["ns_ready"] is None


def test_normalize_devices_group_and_missing_id():
    devices = normalize_devices(
        {
            "devices": [
                {"id": "A1", "name": "Werkstatt", "group": 1},
                {"id": "A2", "group": 27},
                {"name": "ohne ID"},
                "not-a-dict",
            ]
        }
    )
    assert devices[0]["grp"] == "A"
    assert devices[1]["grp"] == "27"
    assert len(devices) == 2


def test_normalize_base_url():
    assert normalize_base_url("http://192.168.1.40/") == "http://192.168.1.40"
    with pytest.raises(ValueError):
        normalize_base_url("ftp://192.168.1.40")
    with pytest.raises(ValueError):
        normalize_base_url("http://user:pass@192.168.1.40")
    with pytest.raises(ValueError):
        normalize_base_url("http://192.168.1.40/?x=1")
    with pytest.raises(ValueError):
        normalize_base_url("http://192.168.1.40/foo")
