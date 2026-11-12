#!/usr/bin/env python3
"""Small fake Awaro gateway for local smoke tests and frontend development.

Run with:  PYTHONPATH=app python app/tests/fake_gateway.py --port 8099
"""

from __future__ import annotations

import argparse
import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

STATUS = {
    "sys": {
        "fw": "3.4.2",
        "hw": "awaro-esp32s3",
        "uptime": 93784,
        "heap": 182344,
    },
    "lns": {"mode": "local", "devices": 3},
    "net": {"ip": "192.168.1.40", "ssid": "lab", "rssi": -67},
    "ns": {"host": "", "port": 0, "ready": True},
}

LNS = {
    "mode": "local",
    "adr": True,
    "usb": False,
    "relay": False,
    "devices": [
        {
            "name": "Werkstatt",
            "id": "70B3D57ED0000001",
            "group": 1,
            "decoder": "Dragino LHT52",
            "cls": "A",
            "fcnt": 128,
            "status": "active",
        },
        {
            "name": "Rauchmelder",
            "id": "70B3D57ED0000002",
            "group": 2,
            "decoder": "TG563A",
            "cls": "A",
            "fcnt": 42,
            "status": "active",
        },
        {
            "name": "Tor",
            "id": "70B3D57ED0000003",
            "group": 2,
            "decoder": "",
            "cls": "A",
            "fcnt": 0,
            "status": "never",
        },
    ],
    "hooks": [
        {
            "name": "Home Assistant",
            "type": "mqtt",
            "url": "mqtt://192.168.1.10:1883",
            "smsg": "uplink",
        }
    ],
    "codecs": [{"model": "TG563A", "spec": "status:u8@4"}],
    "builtins": ["cayenne", "Dragino LHT52", "Milesight"],
}

FIRMWARE = {
    "cur": "3.4.2",
    "hw": "awaro-esp32s3",
    "url": "https://firmware.example/awaro/",
    "list": ["3.4.2", "3.4.1"],
    "avail": "",
    "checked": 1700000000,
    "err": "",
}

EXPORT = {"wifi": {"ssid": "lab"}, "mqtt": {"host": "192.168.1.10"}}
LNS_EXPORT = {
    "devices": [
        {"name": "Werkstatt", "id": "70B3D57ED0000001", "nwkkey": "secret"}
    ],
    "hooks": LNS["hooks"],
    "codecs": LNS["codecs"],
}


class Handler(BaseHTTPRequestHandler):
    server_version = "LoRaDeckFakeGateway/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        auth = self.server.auth  # type: ignore[attr-defined]
        if not auth:
            return True
        expected = "Basic " + base64.b64encode(auth.encode()).decode("ascii")
        if self.headers.get("Authorization") == expected:
            return True
        self._json({"error": "auth required"}, 401)
        return False

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            return
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/status":
            self._json(STATUS)
        elif path == "/lns/api":
            self._json(LNS)
        elif path == "/fw":
            if query.get("action") == ["check"]:
                self.server.checked += 1  # type: ignore[attr-defined]
                self._json({"ok": True})
                return
            firmware = dict(FIRMWARE)
            firmware["checked"] = (
                FIRMWARE["checked"] + self.server.checked  # type: ignore[attr-defined]
            )
            firmware["avail"] = "3.4.3" if self.server.checked else ""  # type: ignore[attr-defined]
            self._json(firmware)
        elif path == "/export":
            self._json(EXPORT)
        elif path == "/lns/export":
            self._json(LNS_EXPORT)
        else:
            self._json({"error": "not found"}, 404)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fake Awaro gateway")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument(
        "--auth", default="", help="optional HTTP Basic auth as user:password"
    )
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.auth = args.auth  # type: ignore[attr-defined]
    server.checked = 0  # type: ignore[attr-defined]
    print(f"Fake gateway on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
