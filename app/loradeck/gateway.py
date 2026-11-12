from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import httpx

from . import db
from .config import Settings


class GatewayError(Exception):
    """Raised when the Awaro gateway cannot be reached or returns bad data."""


def parse_basic_auth(value: str) -> tuple[str, str] | None:
    value = (value or "").strip()
    if not value:
        return None
    if ":" not in value:
        raise ValueError("gateway auth must use the form user:password")
    user, password = value.split(":", 1)
    if not user:
        raise ValueError("gateway auth user must not be empty")
    return user, password


def normalize_base_url(value: str) -> str:
    value = (value or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("gateway URL must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise ValueError("gateway URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("gateway URL must not contain a query or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("gateway URL must not contain a path")
    return value


class GatewayClient:
    def __init__(
        self,
        base_url: str,
        *,
        auth: str = "",
        timeout: float = 8.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        basic = parse_basic_auth(auth)
        self._client = httpx.Client(
            base_url=self.base_url,
            auth=httpx.BasicAuth(*basic) if basic else None,
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GatewayClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        try:
            response = self._client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise GatewayError("Gateway antwortet nicht (Timeout)") from exc
        except httpx.HTTPError as exc:
            raise GatewayError(
                f"Gateway nicht erreichbar ({exc.__class__.__name__})"
            ) from exc
        if response.status_code == 401:
            raise GatewayError("Gateway verlangt HTTP-Basic-Auth (401)")
        if response.status_code == 403:
            raise GatewayError("Gateway verweigert den Zugriff (403)")
        if response.status_code >= 400:
            raise GatewayError(
                f"Gateway antwortet mit HTTP {response.status_code}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise GatewayError("Gateway antwortet nicht mit JSON") from exc
        if not isinstance(data, (dict, list)):
            raise GatewayError("Gateway liefert ein unerwartetes JSON-Format")
        return data

    def _get_object(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = self._get(path, params)
        if not isinstance(data, dict):
            raise GatewayError(f"Gateway liefert für {path} kein JSON-Objekt")
        return data

    def status(self) -> dict[str, Any]:
        return self._get_object("/status")

    def lns(self) -> dict[str, Any]:
        return self._get_object("/lns/api")

    def firmware(self) -> dict[str, Any]:
        return self._get_object("/fw")

    def check_firmware(
        self, attempts: int = 15, delay: float = 2.0
    ) -> dict[str, Any]:
        before = self.firmware()
        checked_before = before.get("checked")
        self._get("/fw", params={"action": "check"})
        current = before
        for _ in range(max(1, attempts)):
            if delay > 0:
                time.sleep(delay)
            current = self.firmware()
            if current.get("checked") and current.get("checked") != checked_before:
                return current
        return current

    def export_config(self, secrets: bool = False) -> dict[str, Any]:
        params = {"secrets": "1"} if secrets else None
        return self._get_object("/export", params)

    def export_lns(self) -> dict[str, Any]:
        return self._get_object("/lns/export")


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.lstrip("-").isdigit():
            return int(text)
    return None


def normalize_status(payload: dict[str, Any]) -> dict[str, Any]:
    sysd = payload.get("sys")
    lns = payload.get("lns")
    net = payload.get("net")
    ns = payload.get("ns")
    sysd = sysd if isinstance(sysd, dict) else {}
    lns = lns if isinstance(lns, dict) else {}
    net = net if isinstance(net, dict) else {}
    ns = ns if isinstance(ns, dict) else {}
    ready = ns.get("ready")
    return {
        "fw": str(sysd.get("fw") or ""),
        "hw": str(sysd.get("hw") or ""),
        "uptime": _int_or_none(sysd.get("uptime")),
        "heap": _int_or_none(sysd.get("heap")),
        "ip": str(net.get("ip") or ""),
        "ssid": str(net.get("ssid") or ""),
        "rssi": _int_or_none(net.get("rssi")),
        "mode": str(lns.get("mode") or ""),
        "devices": _int_or_none(lns.get("devices")),
        "ns_ready": None if ready is None else (1 if ready else 0),
    }


def normalize_devices(lns: dict[str, Any]) -> list[dict[str, Any]]:
    raw = lns.get("devices")
    if not isinstance(raw, list):
        return []
    devices: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        dev_id = str(item.get("id") or item.get("dev_id") or "").strip()
        if not dev_id:
            continue
        group = item.get("group")
        if (
            isinstance(group, int)
            and not isinstance(group, bool)
            and 1 <= group <= 26
        ):
            grp = chr(64 + group)
        else:
            grp = str(group or "")
        devices.append(
            {
                "dev_id": dev_id,
                "name": str(item.get("name") or ""),
                "grp": grp,
                "decoder": str(item.get("decoder") or ""),
                "cls": str(item.get("cls") or ""),
                "fcnt": _int_or_none(item.get("fcnt")),
                "status": str(item.get("status") or ""),
            }
        )
    return devices


def build_client(
    settings: Settings, conn, transport: httpx.BaseTransport | None = None
) -> GatewayClient | None:
    url = db.get_setting(conn, "gateway_url", settings.gateway_url).strip()
    if not url:
        return None
    return GatewayClient(
        url,
        auth=settings.gateway_auth,
        timeout=settings.gateway_timeout,
        transport=transport,
    )
