from __future__ import annotations

from dataclasses import replace

import httpx
from fastapi.testclient import TestClient

from loradeck.gateway import GatewayClient
from loradeck.main import create_app

from .conftest import PASSWORD
from .fixtures import EXPORT, FIRMWARE, LNS, LNS_EXPORT, STATUS


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/login", json={"username": "admin", "password": PASSWORD}
    )
    assert response.status_code == 200


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/status":
        return httpx.Response(200, json=STATUS)
    if path == "/lns/api":
        return httpx.Response(200, json=LNS)
    if path == "/fw":
        return httpx.Response(200, json=FIRMWARE)
    if path == "/export":
        return httpx.Response(200, json=EXPORT)
    if path == "/lns/export":
        return httpx.Response(200, json=LNS_EXPORT)
    return httpx.Response(404)


def _failing_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500)


class FastCheckClient(GatewayClient):
    def check_firmware(self, attempts: int = 1, delay: float = 0.0):
        return super().check_firmware(attempts=attempts, delay=delay)


def test_health(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["gateway_configured"] is True
    assert body["version"] == "1.0.0"


def test_session_anonymous(client):
    response = client.get("/api/session")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "username": None}


def test_login_and_logout(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        _login(client)
        assert client.get("/api/session").json()["authenticated"] is True
        client.post("/api/logout")
        assert client.get("/api/session").json()["authenticated"] is False


def test_login_wrong_password(client):
    response = client.post(
        "/api/login", json={"username": "admin", "password": "falsch"}
    )
    assert response.status_code == 401


def test_login_rate_limit(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        for _ in range(5):
            response = client.post(
                "/api/login",
                json={"username": "admin", "password": "falsch"},
            )
            assert response.status_code == 401
        response = client.post(
            "/api/login", json={"username": "admin", "password": PASSWORD}
        )
        assert response.status_code == 429


def test_admin_endpoints_require_auth(client):
    for path in (
        "/api/overview",
        "/api/samples",
        "/api/sensors",
        "/api/integrations",
        "/api/events",
        "/api/firmware",
        "/api/backups",
        "/api/settings",
    ):
        assert client.get(path).status_code == 401, path
    assert client.post("/api/gateway/refresh").status_code == 401


def test_settings_roundtrip(auth_client):
    response = auth_client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["gateway_url"] == "http://gateway.test"
    assert body["poll_interval"] == 60
    assert body["auth_configured"] is False

    response = auth_client.put(
        "/api/settings",
        json={"gateway_url": "http://192.168.1.41/", "poll_interval": 120},
    )
    assert response.status_code == 200
    assert response.json()["gateway_url"] == "http://192.168.1.41"
    assert response.json()["poll_interval"] == 120

    response = auth_client.put(
        "/api/settings",
        json={"gateway_url": "ftp://192.168.1.41", "poll_interval": 120},
    )
    assert response.status_code == 422

    response = auth_client.put(
        "/api/settings",
        json={"gateway_url": "http://192.168.1.41/foo", "poll_interval": 120},
    )
    assert response.status_code == 422

    response = auth_client.put(
        "/api/settings",
        json={"gateway_url": "http://192.168.1.41", "poll_interval": 5},
    )
    assert response.status_code == 422


def test_overview_without_poll(auth_client):
    response = auth_client.get("/api/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["sample"] is None
    assert body["counts"]["sensors"] == 0
    assert body["counts"]["integrations"] == 0


def test_refresh_populates_overview_sensors_and_events(app_factory):
    app = app_factory(_handler)
    with TestClient(app) as client:
        _login(client)
        response = client.post("/api/gateway/refresh")
        assert response.status_code == 200
        assert response.json()["ok"] is True

        overview = client.get("/api/overview").json()
        assert overview["sample"]["online"] is True
        assert overview["sample"]["fw"] == "3.4.2"
        assert overview["counts"]["sensors"] == 3
        assert overview["counts"]["integrations"] == 1
        assert overview["counts"]["decoders"] == 1
        assert overview["counts"]["builtin_decoders"] == 3

        sensors = client.get("/api/sensors").json()
        assert len(sensors) == 3
        assert sensors[0]["dev_id"].startswith("70B3")

        events = client.get("/api/events").json()
        kinds = [item["kind"] for item in events]
        assert "online" in kinds
        assert kinds.count("sensor_new") == 3

        integrations = client.get("/api/integrations").json()
        assert integrations["mode"] == "local"
        assert integrations["adr"] is True
        assert integrations["hooks"][0]["name"] == "Home Assistant"
        assert integrations["codecs"][0]["model"] == "TG563A"
        assert "cayenne" in integrations["builtins"]


def test_refresh_offline_returns_502(app_factory):
    app = app_factory(_failing_handler)
    with TestClient(app) as client:
        _login(client)
        response = client.post("/api/gateway/refresh")
        assert response.status_code == 502
        overview = client.get("/api/overview").json()
        assert overview["sample"]["online"] is False
        assert overview["last_error"]


def test_samples_endpoint(app_factory):
    app = app_factory(_handler)
    with TestClient(app) as client:
        _login(client)
        client.post("/api/gateway/refresh")
        client.post("/api/gateway/refresh")
        samples = client.get("/api/samples?limit=10").json()
        assert len(samples) == 2
        assert samples[-1]["online"] is True


def test_firmware_endpoints(app_factory):
    state = {"checked": FIRMWARE["checked"], "checks": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/fw":
            if request.url.params.get("action") == "check":
                state["checks"] += 1
                state["checked"] += 1
                return httpx.Response(200, json={"ok": True})
            firmware = dict(FIRMWARE)
            firmware["checked"] = state["checked"]
            firmware["avail"] = "3.4.3" if state["checks"] else ""
            return httpx.Response(200, json=firmware)
        return _handler(request)

    app = app_factory(handler, client_cls=FastCheckClient)
    with TestClient(app) as client:
        _login(client)
        response = client.get("/api/firmware")
        assert response.status_code == 200
        assert response.json()["cur"] == "3.4.2"
        response = client.post("/api/firmware/check")
        assert response.status_code == 200
        assert response.json()["avail"] == "3.4.3"


def test_backup_create_download_delete(app_factory):
    app = app_factory(_handler)
    with TestClient(app) as client:
        _login(client)
        response = client.post("/api/backups")
        assert response.status_code == 201
        item = response.json()
        assert item["kind"] == "config+lns"
        assert item["size"] > 0
        assert len(item["sha256"]) == 64

        listing = client.get("/api/backups").json()
        assert len(listing) == 1

        download = client.get(f"/api/backups/{item['id']}/download")
        assert download.status_code == 200
        assert "attachment" in download.headers["content-disposition"]
        document = download.json()
        assert document["backup"]["config_secrets"] is False
        assert "nwkkey" in str(document["lns"])

        response = client.delete(f"/api/backups/{item['id']}")
        assert response.status_code == 204
        assert client.get("/api/backups").json() == []
        assert client.get(f"/api/backups/{item['id']}/download").status_code == 404


def test_backup_requires_gateway(settings):
    app = create_app(replace(settings, gateway_url=""))
    with TestClient(app) as client:
        _login(client)
        assert client.get("/api/firmware").status_code == 400
        assert client.post("/api/backups").status_code == 400
        assert client.post("/api/gateway/refresh").status_code == 400


def test_spa_fallback(settings):
    settings.static_dir.mkdir(parents=True)
    (settings.static_dir / "index.html").write_text(
        "<!doctype html><title>LoRaDeck</title>", encoding="utf-8"
    )
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/sensors")
        assert response.status_code == 200
        assert "LoRaDeck" in response.text
        assert client.get("/api/does-not-exist").status_code == 404
        assert client.get("/api").status_code == 404


def test_origin_check(auth_client):
    response = auth_client.post(
        "/api/logout", headers={"Origin": "http://evil.example"}
    )
    assert response.status_code == 403


def test_overview_event_limit_and_shapes(app_factory):
    app = app_factory(_handler)
    with TestClient(app) as client:
        _login(client)
        client.post("/api/gateway/refresh")
        overview = client.get("/api/overview").json()
        assert isinstance(overview["events"], list)
        assert len(overview["events"]) <= 8
        sample = overview["sample"]
        for key in ("ts", "online", "fw", "hw", "uptime", "heap", "rssi"):
            assert key in sample
