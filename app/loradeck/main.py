from __future__ import annotations

import json
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from . import __version__, backup, db
from .auth import (
    LoginGuard,
    create_session,
    verify_password,
    verify_session,
)
from .config import Settings
from .gateway import GatewayClient, GatewayError, build_client
from .models import LoginIn, SettingsIn
from .poller import Poller, poll_once

logger = logging.getLogger("loradeck")
COOKIE_NAME = "ld_session"


def get_db(request: Request):
    conn = db.connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def require_admin(request: Request) -> str:
    settings = request.app.state.settings
    token = request.cookies.get(COOKIE_NAME)
    user = verify_session(request.app.state.secret, token)
    if user is None or user != settings.admin_user:
        raise HTTPException(status_code=401, detail="Nicht angemeldet")
    return user


def _static_root(request: Request) -> Path:
    return request.app.state.settings.static_dir.resolve()


def _safe_file(root: Path, relative: str) -> Path | None:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _serve_index(request: Request) -> Response:
    index = _static_root(request) / "index.html"
    if not index.is_file():
        return JSONResponse(
            {
                "detail": "Web-Build fehlt. Bitte 'npm run build' im Verzeichnis web ausfuehren."
            },
            status_code=404,
        )
    return FileResponse(
        index,
        media_type="text/html",
        headers={"Cache-Control": "no-cache"},
    )


def _load_lns(conn) -> dict[str, Any]:
    raw = db.get_state(conn, "last_lns", "")
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _client_or_400(request: Request, conn) -> GatewayClient:
    try:
        client = request.app.state.gateway_factory(conn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if client is None:
        raise HTTPException(
            status_code=400,
            detail="Keine Gateway-URL konfiguriert",
        )
    return client


def _hook_list(lns: dict[str, Any]) -> list[dict[str, Any]]:
    hooks = lns.get("hooks")
    if not isinstance(hooks, list):
        return []
    result = []
    for hook in hooks:
        if not isinstance(hook, dict):
            continue
        result.append(
            {
                "name": str(hook.get("name") or ""),
                "type": str(hook.get("type") or ""),
                "url": str(hook.get("url") or ""),
                "smsg": str(hook.get("smsg") or ""),
            }
        )
    return result


def _codec_list(lns: dict[str, Any]) -> list[dict[str, str]]:
    codecs = lns.get("codecs")
    if not isinstance(codecs, list):
        return []
    result = []
    for codec in codecs:
        if not isinstance(codec, dict):
            continue
        result.append(
            {
                "model": str(codec.get("model") or ""),
                "spec": str(codec.get("spec") or ""),
            }
        )
    return result


def _builtin_list(lns: dict[str, Any]) -> list[str]:
    builtins = lns.get("builtins")
    if not isinstance(builtins, list):
        return []
    return [str(item) for item in builtins if item]


def create_app(
    settings: Settings | None = None,
    gateway_factory=None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    secret = settings.secret or secrets.token_hex(32)
    factory = gateway_factory or (
        lambda conn: build_client(settings, conn)
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        settings.backup_dir.mkdir(parents=True, exist_ok=True)
        conn = db.connect(settings.db_path)
        try:
            db.init_db(conn)
            db.ensure_settings(
                conn,
                {
                    "gateway_url": settings.gateway_url,
                    "poll_interval": str(settings.poll_interval),
                },
            )
            logger.info("Database ready (%s)", settings.db_path)
        finally:
            conn.close()
        if not settings.secret:
            logger.warning(
                "LORADECK_SECRET is not set; sessions are invalid after restart"
            )
        poller: Poller | None = None
        if settings.poll_enabled:
            poller = Poller(settings, factory)
            await poller.start()
            app.state.poller = poller
        yield
        if poller is not None:
            await poller.stop()

    app = FastAPI(
        title="LoRaDeck",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.secret = secret
    app.state.login_guard = LoginGuard()
    app.state.gateway_factory = factory

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin:
                parsed = urlparse(origin)
                if not parsed.netloc or parsed.netloc != request.headers.get(
                    "host", ""
                ):
                    return JSONResponse(
                        {"detail": "Origin nicht erlaubt"}, status_code=403
                    )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        return response

    @app.get("/healthz")
    def healthz(request: Request):
        settings = request.app.state.settings
        configured = False
        try:
            conn = db.connect(settings.db_path)
            try:
                conn.execute("SELECT 1").fetchone()
                configured = bool(
                    db.get_setting(conn, "gateway_url", settings.gateway_url).strip()
                )
            finally:
                conn.close()
            db_state = "ok"
        except Exception:
            logger.exception("Healthcheck database failure")
            db_state = "error"
        status_code = 200 if db_state == "ok" else 503
        return JSONResponse(
            {
                "status": "ok" if db_state == "ok" else "error",
                "db": db_state,
                "version": __version__,
                "gateway_configured": configured,
            },
            status_code=status_code,
        )

    @app.get("/api/session")
    def api_session(request: Request):
        settings = request.app.state.settings
        token = request.cookies.get(COOKIE_NAME)
        user = verify_session(request.app.state.secret, token)
        authenticated = user is not None and user == settings.admin_user
        return {
            "authenticated": authenticated,
            "username": settings.admin_user if authenticated else None,
        }

    @app.post("/api/login")
    def api_login(payload: LoginIn, request: Request, response: Response):
        settings = request.app.state.settings
        client = request.client.host if request.client else "unknown"
        guard: LoginGuard = request.app.state.login_guard
        if guard.blocked(client):
            raise HTTPException(
                status_code=429,
                detail="Zu viele Fehlversuche. Bitte spaeter erneut versuchen.",
            )
        if not settings.admin_hash:
            raise HTTPException(
                status_code=503, detail="Admin-Zugang ist nicht konfiguriert"
            )
        valid_user = payload.username == settings.admin_user
        valid_password = verify_password(payload.password, settings.admin_hash)
        if not (valid_user and valid_password):
            guard.fail(client)
            raise HTTPException(
                status_code=401, detail="Benutzername oder Passwort falsch"
            )
        guard.reset(client)
        token = create_session(
            request.app.state.secret, settings.admin_user, settings.session_ttl
        )
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=settings.session_ttl,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            path="/",
        )
        return {"authenticated": True, "username": settings.admin_user}

    @app.post("/api/logout")
    def api_logout(response: Response):
        response.delete_cookie(COOKIE_NAME, path="/")
        return {"authenticated": False}

    @app.get("/api/overview")
    def api_overview(
        request: Request,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        settings = request.app.state.settings
        gateway_url = db.get_setting(conn, "gateway_url", settings.gateway_url)
        try:
            poll_interval = int(
                db.get_setting(conn, "poll_interval", str(settings.poll_interval))
            )
        except ValueError:
            poll_interval = settings.poll_interval
        lns = _load_lns(conn)
        counter = db.counts(conn)
        counter["integrations"] = len(_hook_list(lns))
        counter["decoders"] = len(_codec_list(lns))
        counter["builtin_decoders"] = len(_builtin_list(lns))
        return {
            "configured": bool(gateway_url.strip()),
            "auth_configured": bool(settings.gateway_auth),
            "gateway_url": gateway_url,
            "poll_interval": poll_interval,
            "poll_enabled": settings.poll_enabled,
            "last_poll": db.get_state(conn, "last_poll_ts", ""),
            "last_error": db.get_state(conn, "last_error", ""),
            "sample": db.latest_sample(conn),
            "counts": counter,
            "events": db.list_events(conn, 8),
            "version": __version__,
        }

    @app.get("/api/samples")
    def api_samples(
        limit: int = 120,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        limit = max(1, min(500, limit))
        return db.recent_samples(conn, limit)

    @app.get("/api/sensors")
    def api_sensors(
        _: str = Depends(require_admin), conn=Depends(get_db)
    ):
        return db.list_sensors(conn)

    @app.get("/api/integrations")
    def api_integrations(
        _: str = Depends(require_admin), conn=Depends(get_db)
    ):
        lns = _load_lns(conn)
        return {
            "mode": str(lns.get("mode") or ""),
            "adr": lns.get("adr") if "adr" in lns else None,
            "usb": lns.get("usb") if "usb" in lns else None,
            "relay": lns.get("relay") if "relay" in lns else None,
            "hooks": _hook_list(lns),
            "codecs": _codec_list(lns),
            "builtins": _builtin_list(lns),
            "updated_at": db.get_state(conn, "last_poll_ts", ""),
        }

    @app.get("/api/events")
    def api_events(
        limit: int = 50,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        limit = max(1, min(200, limit))
        return db.list_events(conn, limit)

    @app.post("/api/gateway/refresh")
    def api_refresh(
        request: Request,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        client = _client_or_400(request, conn)
        try:
            result = poll_once(conn, request.app.state.settings, client)
        finally:
            client.close()
        if not result["ok"]:
            raise HTTPException(
                status_code=502,
                detail=result.get("error") or "Gateway nicht erreichbar",
            )
        return result

    @app.get("/api/firmware")
    def api_firmware(
        request: Request,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        client = _client_or_400(request, conn)
        try:
            return client.firmware()
        except GatewayError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        finally:
            client.close()

    @app.post("/api/firmware/check")
    def api_firmware_check(
        request: Request,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        client = _client_or_400(request, conn)
        try:
            return client.check_firmware()
        except GatewayError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        finally:
            client.close()

    @app.get("/api/backups")
    def api_backups(
        _: str = Depends(require_admin), conn=Depends(get_db)
    ):
        return db.list_backups(conn)

    @app.post("/api/backups", status_code=201)
    def api_backup_create(
        request: Request,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        client = _client_or_400(request, conn)
        try:
            return backup.create_backup(
                conn, request.app.state.settings, client
            )
        except GatewayError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        finally:
            client.close()

    @app.get("/api/backups/{backup_id}/download")
    def api_backup_download(
        backup_id: int,
        request: Request,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        item = db.get_backup(conn, backup_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Backup nicht gefunden")
        path = backup.backup_path(request.app.state.settings, item)
        if path is None:
            raise HTTPException(status_code=404, detail="Backup-Datei fehlt")
        return FileResponse(
            path,
            media_type="application/json",
            filename=str(item["filename"]),
        )

    @app.delete("/api/backups/{backup_id}", status_code=204)
    def api_backup_delete(
        backup_id: int,
        request: Request,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        try:
            backup.delete_backup(
                conn, request.app.state.settings, backup_id
            )
        except db.NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return Response(status_code=204)

    @app.get("/api/settings")
    def api_settings_get(
        request: Request,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        settings = request.app.state.settings
        gateway_url = db.get_setting(conn, "gateway_url", settings.gateway_url)
        try:
            poll_interval = int(
                db.get_setting(conn, "poll_interval", str(settings.poll_interval))
            )
        except ValueError:
            poll_interval = settings.poll_interval
        return {
            "gateway_url": gateway_url,
            "poll_interval": poll_interval,
            "auth_configured": bool(settings.gateway_auth),
            "poll_enabled": settings.poll_enabled,
            "version": __version__,
        }

    @app.put("/api/settings")
    def api_settings_put(
        payload: SettingsIn,
        request: Request,
        _: str = Depends(require_admin),
        conn=Depends(get_db),
    ):
        db.set_setting(conn, "gateway_url", payload.gateway_url)
        db.set_setting(conn, "poll_interval", str(payload.poll_interval))
        return api_settings_get(request, _, conn)

    @app.get("/")
    def index(request: Request):
        return _serve_index(request)

    @app.get("/{full_path:path}")
    def spa(full_path: str, request: Request):
        if full_path == "api" or full_path.startswith(("api/", "healthz")):
            raise HTTPException(status_code=404, detail="Not found")
        root = _static_root(request)
        file = _safe_file(root, full_path)
        if file is not None:
            headers = (
                {"Cache-Control": "public, max-age=31536000, immutable"}
                if full_path.startswith("assets/")
                else {}
            )
            return FileResponse(file, headers=headers)
        return _serve_index(request)

    return app


app = create_app()
