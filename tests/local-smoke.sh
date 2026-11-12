#!/usr/bin/env bash
#
# local-smoke.sh - startet Fake-Gateway und LoRaDeck lokal, prueft die Kernpfade.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${VENV:-$ROOT/app/.venv}"
PORT="${PORT:-8091}"
GW_PORT="${GW_PORT:-8099}"
TMP="$(mktemp -d)"
APP_PID=""
GW_PID=""

msg() { printf '\033[34m[SMOKE]\033[0m %s\n' "$*"; }
ok()  { printf '\033[32m[OK]\033[0m    %s\n' "$*"; }
die() { printf '\033[31m[FAIL]\033[0m  %s\n' "$*" >&2; exit 1; }

cleanup() {
  for pid in "$APP_PID" "$GW_PID"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
  rm -rf "$TMP"
}
trap cleanup EXIT

[[ -x "$VENV/bin/python" ]] || die "venv fehlt: $VENV (zuerst tests/api.sh ausfuehren)"
[[ -f "$ROOT/web/dist/index.html" ]] || die "web/dist fehlt (cd web && npm ci && npm run build)"

pick_port() {
  "$VENV/bin/python" - "$1" <<'PY'
import socket
import sys

sock = socket.socket()
try:
    sock.bind(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
}

if ! pick_port "$PORT"; then
  OLD_PORT="$PORT"
  PORT="$("$VENV/bin/python" -c \
    'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
  msg "Port ${OLD_PORT} belegt, nutze freien Port ${PORT}"
fi
if ! pick_port "$GW_PORT"; then
  OLD_GW_PORT="$GW_PORT"
  GW_PORT="$("$VENV/bin/python" -c \
    'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
  msg "Gateway-Port ${OLD_GW_PORT} belegt, nutze freien Port ${GW_PORT}"
fi

msg "Starte Fake-Gateway auf Port ${GW_PORT}"
(
  cd "$ROOT/app"
  exec env PYTHONPATH="$ROOT/app" \
    "$VENV/bin/python" "$ROOT/app/tests/fake_gateway.py" --port "$GW_PORT"
) > "$TMP/gateway.log" 2>&1 &
GW_PID=$!

gateway_ready=0
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${GW_PORT}/status" >/dev/null 2>&1; then
    gateway_ready=1
    break
  fi
  sleep 0.25
done
[[ "$gateway_ready" == "1" ]] || { tail -n 40 "$TMP/gateway.log"; die "Fake-Gateway startet nicht"; }
ok "Fake-Gateway antwortet"

HASH="$(PYTHONPATH="$ROOT/app" "$VENV/bin/python" -c \
  'from loradeck.auth import hash_password; print(hash_password("smoke-pass"))')"

msg "Starte Uvicorn auf Port ${PORT}"
(
  cd "$ROOT/app"
  exec env \
    LORADECK_DB="$TMP/smoke.db" \
    LORADECK_STATIC="$ROOT/web/dist" \
    LORADECK_SECRET="smoke-secret" \
    LORADECK_ADMIN_USER="admin" \
    LORADECK_ADMIN_HASH="$HASH" \
    LORADECK_GATEWAY_URL="http://127.0.0.1:${GW_PORT}" \
    LORADECK_POLL_ENABLED="0" \
    LORADECK_BACKUP_DIR="$TMP/backups" \
    LORADECK_COOKIE_SECURE="0" \
    "$VENV/bin/uvicorn" loradeck.main:app --host 127.0.0.1 --port "$PORT"
) > "$TMP/server.log" 2>&1 &
APP_PID=$!

ready=0
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.5
done
[[ "$ready" == "1" ]] || { tail -n 60 "$TMP/server.log"; die "Server startet nicht"; }
ok "Health: $(curl -fsS "http://127.0.0.1:${PORT}/healthz")"

code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/")"
[[ "$code" == "200" ]] || die "Startseite liefert HTTP ${code}"
ok "SPA-Startseite: HTTP ${code}"

code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/sensors")"
[[ "$code" == "200" ]] || die "SPA-Fallback /sensors liefert HTTP ${code}"
ok "SPA-Fallback /sensors: HTTP ${code}"

code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/api/sensors")"
[[ "$code" == "401" ]] || die "Sensoren ohne Login liefern HTTP ${code} statt 401"
ok "API ohne Login: HTTP 401"

code="$(curl -s -o /dev/null -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"falsch"}' \
  "http://127.0.0.1:${PORT}/api/login")"
[[ "$code" == "401" ]] || die "Falsches Login liefert HTTP ${code} statt 401"
ok "Falsches Login: HTTP 401"

curl -fsS -c "$TMP/cookies" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"smoke-pass"}' \
  "http://127.0.0.1:${PORT}/api/login" >/dev/null
ok "Login korrekt"

curl -fsS -b "$TMP/cookies" -X POST \
  "http://127.0.0.1:${PORT}/api/gateway/refresh" >/dev/null
ok "Gateway-Refresh"

count="$(curl -fsS -b "$TMP/cookies" "http://127.0.0.1:${PORT}/api/sensors" | \
  "$VENV/bin/python" -c 'import json,sys; print(len(json.load(sys.stdin)))')"
[[ "$count" == "3" ]] || die "Sensoren erwartet: 3, gefunden: ${count}"
ok "Sensoren: ${count}"

found="$(curl -fsS -b "$TMP/cookies" "http://127.0.0.1:${PORT}/api/sensors" | \
  "$VENV/bin/python" -c 'import json,sys; names=[s["name"] for s in json.load(sys.stdin)]; print("Werkstatt" in names)')"
[[ "$found" == "True" ]] || die "Sensor 'Werkstatt' fehlt in der Liste"
ok "Sensor-Daten enthalten Werkstatt"

hooks="$(curl -fsS -b "$TMP/cookies" "http://127.0.0.1:${PORT}/api/integrations" | \
  "$VENV/bin/python" -c 'import json,sys; print(len(json.load(sys.stdin)["hooks"]))')"
[[ "$hooks" == "1" ]] || die "Hooks erwartet: 1, gefunden: ${hooks}"
ok "Integrationen: ${hooks} Hook"

firmware="$(curl -fsS -b "$TMP/cookies" -X POST \
  "http://127.0.0.1:${PORT}/api/firmware/check" | \
  "$VENV/bin/python" -c 'import json,sys; print(json.load(sys.stdin).get("avail", ""))')"
[[ "$firmware" == "3.4.3" ]] || die "Firmware-Check liefert '${firmware}' statt '3.4.3'"
ok "Firmware-Check: ${firmware}"

created="$(curl -fsS -b "$TMP/cookies" -X POST "http://127.0.0.1:${PORT}/api/backups")"
BACKUP_ID="$(printf '%s' "$created" | "$VENV/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
ok "Backup erstellt (ID ${BACKUP_ID})"

code="$(curl -s -o /dev/null -w '%{http_code}' -b "$TMP/cookies" \
  "http://127.0.0.1:${PORT}/api/backups/${BACKUP_ID}/download")"
[[ "$code" == "200" ]] || die "Backup-Download liefert HTTP ${code}"
ok "Backup-Download: HTTP ${code}"

code="$(curl -s -o /dev/null -w '%{http_code}' -b "$TMP/cookies" \
  -X DELETE "http://127.0.0.1:${PORT}/api/backups/${BACKUP_ID}")"
[[ "$code" == "204" ]] || die "Backup-Loeschen liefert HTTP ${code}"
ok "Backup geloescht: HTTP 204"

code="$(curl -s -o /dev/null -w '%{http_code}' -b "$TMP/cookies" \
  -H 'Content-Type: application/json' \
  -d '{"gateway_url":"ftp://example","poll_interval":60}' \
  -X PUT "http://127.0.0.1:${PORT}/api/settings")"
[[ "$code" == "422" ]] || die "Ungueltige Settings liefern HTTP ${code} statt 422"
ok "Settings-Validierung: HTTP 422"

curl -fsS -b "$TMP/cookies" -c "$TMP/cookies" -X POST \
  "http://127.0.0.1:${PORT}/api/logout" >/dev/null
code="$(curl -s -o /dev/null -w '%{http_code}' -b "$TMP/cookies" \
  "http://127.0.0.1:${PORT}/api/overview")"
[[ "$code" == "401" ]] || die "Nach Logout liefert Overview HTTP ${code} statt 401"
ok "Nach Logout: HTTP 401"

echo
ok "Lokaler Smoke-Test bestanden."
