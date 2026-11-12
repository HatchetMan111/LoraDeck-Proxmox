from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

from . import db
from .config import Settings
from .gateway import (
    GatewayClient,
    GatewayError,
    build_client,
    normalize_devices,
    normalize_status,
)

logger = logging.getLogger("loradeck.poller")

ClientFactory = Callable[[Any], GatewayClient | None]


def _poll_interval(conn, settings: Settings) -> int:
    try:
        value = int(
            db.get_setting(conn, "poll_interval", str(settings.poll_interval))
        )
    except ValueError:
        value = settings.poll_interval
    return max(15, min(3600, value))


def poll_once(conn, settings: Settings, client: GatewayClient) -> dict[str, Any]:
    now = db.utc_now()
    try:
        status_payload = client.status()
        lns_payload = client.lns()
    except GatewayError as exc:
        message = str(exc)
        db.record_sample(conn, {"ts": now, "online": False, "error": message})
        previous = db.get_state(conn, "last_online", "")
        if previous != "0":
            db.add_event(
                conn, "offline", f"Gateway nicht erreichbar: {message}", now
            )
        db.set_state(conn, "last_online", "0", now)
        db.set_state(conn, "last_error", message, now)
        db.set_state(conn, "last_poll_ts", now, now)
        return {"ok": False, "error": message, "ts": now}

    status = normalize_status(status_payload)
    devices = normalize_devices(lns_payload)
    sample: dict[str, Any] = {"ts": now, "online": True, **status, "error": ""}
    if sample.get("devices") is None:
        sample["devices"] = len(devices)
    db.record_sample(conn, sample)

    previous_online = db.get_state(conn, "last_online", "")
    if previous_online != "1":
        db.add_event(conn, "online", "Gateway erreichbar", now)

    previous_fw = db.get_state(conn, "last_fw", "")
    if status["fw"] and previous_fw and status["fw"] != previous_fw:
        db.add_event(
            conn,
            "firmware",
            f"Firmware {previous_fw} → {status['fw']}",
            now,
        )
    if status["fw"]:
        db.set_state(conn, "last_fw", status["fw"], now)

    for change in db.upsert_sensors(conn, devices, now):
        db.add_event(conn, change["kind"], change["message"], now)

    db.set_state(
        conn, "last_status", json.dumps(status_payload, ensure_ascii=False), now
    )
    db.set_state(
        conn, "last_lns", json.dumps(lns_payload, ensure_ascii=False), now
    )
    db.set_state(conn, "last_online", "1", now)
    db.set_state(conn, "last_error", "", now)
    db.set_state(conn, "last_poll_ts", now, now)
    db.prune_events(conn)
    return {
        "ok": True,
        "ts": now,
        "devices": len(devices),
        "status": status,
    }


class Poller:
    def __init__(
        self, settings: Settings, client_factory: ClientFactory | None = None
    ) -> None:
        self.settings = settings
        self.client_factory = client_factory or (
            lambda conn: build_client(settings, conn)
        )
        self._task: asyncio.Task[None] | None = None
        self._stopping: asyncio.Event | None = None

    async def start(self) -> None:
        self._stopping = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="loradeck-poller")

    async def stop(self) -> None:
        if self._stopping is not None:
            self._stopping.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        assert self._stopping is not None
        while not self._stopping.is_set():
            interval = await asyncio.to_thread(self._tick)
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    def _tick(self) -> int:
        conn = db.connect(self.settings.db_path)
        try:
            interval = _poll_interval(conn, self.settings)
            try:
                client = self.client_factory(conn)
            except ValueError as exc:
                logger.warning("Gateway-Konfiguration ungültig: %s", exc)
                return interval
            if client is None:
                return interval
            try:
                result = poll_once(conn, self.settings, client)
                if not result["ok"]:
                    logger.warning("Gateway offline: %s", result.get("error"))
            except Exception:
                logger.exception("Poll fehlgeschlagen")
            finally:
                client.close()
            return interval
        finally:
            conn.close()
