from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from loradeck.auth import hash_password
from loradeck.config import Settings
from loradeck.gateway import GatewayClient
from loradeck.main import create_app

PASSWORD = "test-pass"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        db_path=tmp_path / "test.db",
        static_dir=tmp_path / "static",
        secret="test-secret",
        admin_user="admin",
        admin_hash=hash_password(PASSWORD),
        session_ttl=43200,
        cookie_secure=False,
        gateway_url="http://gateway.test",
        gateway_auth="",
        poll_interval=60,
        poll_enabled=False,
        backup_dir=tmp_path / "backups",
        gateway_timeout=5.0,
    )


@pytest.fixture
def app_factory(settings):
    def make(handler, client_cls=GatewayClient):
        def factory(conn):
            return client_cls(
                "http://gateway.test",
                transport=httpx.MockTransport(handler),
            )

        return create_app(settings, gateway_factory=factory)

    return make


@pytest.fixture
def client(settings):
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_client(settings):
    app = create_app(settings)
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/login",
            json={"username": "admin", "password": PASSWORD},
        )
        assert response.status_code == 200
        yield test_client
