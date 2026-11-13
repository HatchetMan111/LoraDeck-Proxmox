# Test-Evidenz

**Datum:** 2026-11-12
**Umgebung:** Linux, Python 3.12.3, Node.js 22.23.2, npm 10.9.8
**Status:** lokale Tests grün; Proxmox-/Hardware-Test offen

## Lokale Ergebnisse

### Backend

```text
$ bash tests/api.sh
collected 42 items
tests/test_api.py ................. [ 40%]
tests/test_db.py ..........         [ 64%]
tests/test_gateway.py ..........    [ 88%]
tests/test_poller.py .....          [100%]
42 passed, 1 warning in 7.12s
```

Abgedeckt: Login/Logout, Rate-Limit, Session-Schutz, Settings-Validierung,
Gateway-Refresh, Offline-Übergang, Firmware-Check-Loop, Sensor-Upsert und
Status-Events, Backup-CRUD, SPA-Fallback, Origin-Prüfung sowie
SQLite-Nutzung über Thread-Grenzen.

Einzige Warnung: Starlette-Deprecation zu `anyio.abc.BlockingPortal` (TestClient).

### Frontend

```text
$ cd web && npm test
✓ src/lib/format.test.ts (9 tests)

$ npm run build
✓ 49 modules transformed
dist/index.html                 0.51 kB
dist/assets/index-*.css        12.68 kB
dist/assets/index-*.js        198.04 kB
✓ built in 3.49s
```

### Statische Prüfungen

```text
$ bash tests/static-checks.sh
Alle statischen Pruefungen bestanden.
```

Geprüft: `bash -n`, `shellcheck`, systemd-Härtung, Host-/Container-Installer,
Repo-Struktur und README-Einzeiler.

### Installer-CT-ID-Kollision (simuliert)

Die Auswahllogik wurde mit Stub-Kommandos ohne Proxmox geprüft:

```text
pvesh nextid -> 110
CT 110 -> hostname: releasenotes
=> WARN: CT 110 ist belegt (releasenotes) - naechste freie ID
=> CTID=111

pct create 111 -> "already exists"
=> WARN: CT 111 ist inzwischen belegt - naechste freie ID
=> erstellt als CTID=112
```

Damit werden fremde Container nicht überschrieben; `--force` greift nur noch
bei explizit angegebener `--ctid`.

### Lokaler Smoke-Test

```text
$ bash tests/local-smoke.sh
Health: {"status":"ok","db":"ok","version":"1.0.0","gateway_configured":true}
SPA-Startseite: HTTP 200
SPA-Fallback /sensors: HTTP 200
API ohne Login: HTTP 401
Falsches Login: HTTP 401
Login korrekt
Gateway-Refresh
Sensoren: 3
Sensor-Daten enthalten Werkstatt
Integrationen: 1 Hook
Firmware-Check: 3.4.3
Backup erstellt (ID 1)
Backup-Download: HTTP 200
Backup geloescht: HTTP 204
Settings-Validierung: HTTP 422
Nach Logout: HTTP 401
Lokaler Smoke-Test bestanden.
```

Der Test nutzt `app/tests/fake_gateway.py`; Ports `8091`/`8099` waren belegt,
daher wählte das Skript automatisch freie Ports.

## Visuelle Prüfung

Die gebaute SPA wurde mit headless Chromium (1440×1100) gegen einen echten
Uvicorn-Prozess und das Fake-Gateway geprüft: Login, Übersicht, Sensoren,
Integrationen, Firmware, Backups und Einstellungen.

Dabei gefunden und behoben:

- SQLite-Verbindung wurde in einem anderen Thread geschlossen als geöffnet
  (`check_same_thread`). Der Fehler trat nur unter echtem Uvicorn auf, nicht im
  TestClient. Regressionstest ergänzt.
- Inline-`<code>` in Hinweisboxen wurde durch `display: flex` zur vollbreiten
  Zeile; die Backup-Warnung ist jetzt wieder Fließtext.

## Nicht ausgeführt

Diese Schritte brauchen einen Proxmox-Host bzw. echte Hardware und wurden hier
nicht ausgeführt:

- echter LXC-Install über `install/loradeck.sh`
- Reboot-Test (`tests/reboot-test.sh`) inkl. `onboot: 1`
- Verbindung zu einem echten Awaro-Gateway
- Firmware-Prüfung/Installation an echter Hardware
- MQTT-Hook und Home-Assistant-Template mit echten Payloads
- ufw-Verhalten im unprivilegierten LXC

## Offener Betreiber-Schritt

Auf dem Proxmox-Host:

```bash
bash tests/reboot-test.sh --ctid <ID>
```

Erwartet: Dienst `loradeck` ist vor und nach dem Reboot aktiv, `/healthz`
antwortet, `boot_id` ändert sich.
