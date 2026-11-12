# LoRaDeck – Design Spec

**Datum:** 2026-11-12
**Status:** Approved (Design), bereit für Implementierungsplan
**Repo:** https://github.com/HatchetMan111/loradeck-proxmox
**App-ID:** `loradeck` · **Port:** `8080` · **CT-Hostname:** `loradeck`

## 1. Ziel

LoRaDeck ist eine lokale Companion- und Monitoring-Oberfläche für Awaro-
LoRaWAN-Gateways. Es bündelt den Zustand eines Gateways, die deklarierten
Sensoren, Integrationen, Decoder-Tabellen und Firmware-Informationen in einer
übersichtlichen Web-UI. LoRaDeck spricht das Gateway ausschließlich über dessen
HTTP-API an, speichert Verlaufsdaten lokal in SQLite und benötigt weder Cloud
noch MQTT-Broker noch USB-Zugriff.

LoRaDeck ist ein **inoffizielles** Projekt. „Awaro" ist eine Marke ihres
jeweiligen Inhabers; LoRaDeck steht in keiner Verbindung zum Hersteller.

## 2. Scope Version 1

Enthalten:

- Gateway-Status: Firmware, Hardware, Uptime, freier Heap, IP/SSID/RSSI,
  LoRaWAN-Modus, NS-Bereitschaft, Anzahl deklarierter Sensoren
- Verlauf von Uptime, Heap, RSSI und Sensoranzahl als Sparklines
- Sensor-Register: Name, DevEUI/ID, Gruppe, Decoder, Klasse, FCnt, Status,
  zuletzt gesehen
- Integrationen: Hooks (Name, Typ, URL, Nachricht) und Decoder-Inventar
  (Brand-Engines, Modell-Decoder, eigene Decoder-Tabellen)
- Firmware-Übersicht und asynchroner Update-Check (kein Installieren)
- Backups: Konfiguration ohne Secrets plus LoRaWAN-Export, Download, Löschen
- Ereignisprotokoll: online/offline, Firmware-Wechsel, neue Sensoren,
  Statuswechsel von Sensoren
- Einstellungen: Gateway-URL und Poll-Intervall zur Laufzeit
- Single-Admin-Login mit automatisch erzeugtem Passwort
- Dark/Light-Theme, responsive UI, deutsche Oberfläche, lokale Assets
- Healthcheck unter `/healthz`

Nicht enthalten (bewusst YAGNI):

- Downlinks, ADR-Kommandos, Codec-Test, USB/Serial, eigener MQTT-Broker
- Messwert-Historie und Messwert-Diagramme (die dokumentierte Gateway-HTTP-API
  liefert keine Uplink-Historie; dafür `/lns` am Gateway, MQTT oder Home
  Assistant nutzen)
- Firmware-Installation über die UI (nur Check; Installieren per `awaro`)
- Mehrere Gateways pro Instanz, Rollen/Mehrbenutzer, OAuth, Audit-Log
- Matter, Cloud-Sync, Telemetrie, externe CDNs

## 3. Architektur

```
Browser ──HTTP──> FastAPI (uvicorn) ──sqlite3──> /var/lib/loradeck/loradeck.db
                        │
                        ├── statische Dateien: /opt/loradeck/web/dist
                        │
                        └── HTTP (LAN) ──> Awaro-Gateway
                                           /status
                                           /lns/api
                                           /fw
                                           /export, /lns/export
```

- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLite (stdlib `sqlite3`),
  Pydantic über FastAPI, `httpx` für Gateway-Aufrufe.
- **Auth:** stdlib `hashlib.scrypt` und HMAC-signierte Cookies, keine
  Auth-/Session-Bibliothek.
- **Poller:** ein asyncio-Hintergrundtask pro Prozess; jeder Tick öffnet eine
  eigene SQLite-Verbindung und ruft das Gateway mit kurzem Timeout auf.
- **Frontend:** React 18, Vite 6, TypeScript, React Router. Kein CSS-Framework;
  eigenes Designsystem über CSS-Variablen.
- **Betrieb:** eine systemd-Unit `loradeck.service`, `Restart=always`,
  `After=network-online.target`, `onboot=1` im Container.

## 4. Repository-Struktur

```
loradeck-proxmox/
├── install/loradeck.sh               # Host-Installer (Proxmox)
├── install/loradeck-inner.sh         # Container-Installer
├── systemd/loradeck.service          # Unit-Template (@APP_DIR@/@APP_PORT@)
├── app/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml
│   ├── loradeck/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── auth.py
│   │   ├── db.py
│   │   ├── gateway.py
│   │   ├── poller.py
│   │   ├── backup.py
│   │   ├── models.py
│   │   └── main.py
│   └── tests/
├── web/                              # React/Vite/TS
├── tests/{static-checks,api,local-smoke,reboot-test}.sh
├── docs/superpowers/specs|plans/
├── .github/workflows/ci.yml
└── README.md
```

## 5. Datenmodell

`settings` – Schlüssel/Wert, von der UI änderbar:

| Key | Bedeutung |
|---|---|
| `gateway_url` | Basis-URL des Gateways, z. B. `http://192.168.1.40` |
| `poll_interval` | Poll-Intervall in Sekunden, 15–3600 |

`state` – letzter bekannter Zustand (JSON/Text), u. a. `last_status`,
`last_lns`, `last_online`, `last_fw`, `last_error`, `last_poll_ts`.

`gateway_samples` – Zeitreihe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | INTEGER PK | |
| `ts` | TEXT | UTC ISO-8601 |
| `online` | INTEGER | 0/1 |
| `fw`, `hw` | TEXT | Firmware/Hardware |
| `uptime`, `heap` | INTEGER | Sekunden, Bytes |
| `ip`, `ssid` | TEXT | Netzwerk |
| `rssi` | INTEGER | dBm |
| `mode` | TEXT | `local`/`forward` |
| `ns_ready` | INTEGER | 0/1/NULL |
| `devices` | INTEGER | deklarierte Sensoren |
| `error` | TEXT | Fehlertext bei offline |

`sensors` – Register, `dev_id` UNIQUE; Felder `name`, `grp`, `decoder`,
`cls`, `fcnt`, `status`, `first_seen`, `last_seen`, `updated_at`.

`events` – `ts`, `kind`, `message`; Indizes auf `ts DESC`.

`backups` – `ts`, `filename` UNIQUE, `kind`, `size`, `sha256`.

## 6. HTTP-API

Öffentlich:

- `GET /healthz` → `{status, db, version, gateway_configured}`; 503 bei DB-Fehler
- `GET /api/session` → `{authenticated, username}`
- `POST /api/login` `{username,password}` → setzt HttpOnly-Cookie
- `POST /api/logout` → löscht Cookie

Admin (Cookie erforderlich):

- `GET /api/overview` → letzter Sample, Zähler, letzte Ereignisse, Konfigstatus
- `GET /api/samples?limit=120` → Zeitreihe (max. 500)
- `GET /api/sensors` → Sensor-Register
- `GET /api/integrations` → Hooks, Decoder, Modus/ADR/USB/Relay
- `GET /api/events?limit=50` → Ereignisse (max. 200)
- `POST /api/gateway/refresh` → sofortiger Poll; 502 bei Gateway-Fehler
- `GET /api/firmware` → Live-Abfrage `/fw`; 400 ohne Gateway, 502 bei Fehler
- `POST /api/firmware/check` → `/fw?action=check`, danach auf Ergebnis warten
- `GET /api/backups` → Metadaten
- `POST /api/backups` → Backup erzeugen (Konfig ohne Secrets + LoRaWAN)
- `GET /api/backups/{id}/download` → JSON-Datei
- `DELETE /api/backups/{id}` → 204
- `GET /api/settings` → Gateway-URL, Intervall, `auth_configured`, Version
- `PUT /api/settings` `{gateway_url,poll_interval}` → validiert und speichert

SPA: `/` und alle Nicht-API-Pfade liefern `index.html`; vorhandene Dateien
werden direkt ausgeliefert. `/assets/*` mit langem Cache, `index.html` ohne Cache.

## 7. Gateway-Anbindung

Basis-URL ohne Pfad, nur `http`/`https`. Optionale HTTP-Basic-Auth wird als
`user:pass` über den Installer in `/etc/loradeck/config.env` (0600, root)
gesetzt und nie an den Browser ausgeliefert; die UI zeigt nur
`auth_configured: true/false`.

Genutzte Endpunkte (Awaro-Firmware, dokumentiert über die MIT-CLI `awaro`):

| Endpunkt | Zweck |
|---|---|
| `GET /status` | `sys{fw,hw,uptime,heap}`, `lns{mode,devices}`, `net{ip,ssid,rssi}`, `ns{host,port,ready}` |
| `GET /lns/api` | `mode, adr, usb, relay, devices[], hooks[], codecs[], builtins[]` |
| `GET /fw` | `cur, hw, url, list[], avail, checked, err` |
| `GET /fw?action=check` | stößt asynchronen Update-Check an |
| `GET /export` | Konfiguration ohne Secrets |
| `GET /lns/export` | LoRaWAN-Konfiguration inkl. Sensor-Schlüssel |

`/fw?action=check` ist asynchron: LoRaDeck pollt `/fw`, bis sich `checked`
ändert (max. 15 × 2 s). Fehler werden als `GatewayError` mit klarer
deutscher Meldung weitergereicht.

## 8. Auth & Sicherheit

- Admin-Passwort beim Install erzeugen (alternativ `--admin-password`), als
  `scrypt$N$r$p$salt$hash` in `/etc/loradeck/config.env` (0600, root).
- Login-Bremse: max. 5 Fehlversuche pro IP in 5 Minuten, dann 429.
- Session-Cookie `ld_session`, HttpOnly, SameSite=Lax, 12 h, HMAC-SHA256.
- Schreibende Anfragen mit fremdem `Origin`-Header werden mit 403 abgewiesen.
- Security-Header: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, restriktive CSP ohne externe Quellen.
- Gateway-Basic-Auth und Admin-Hash werden nie geloggt oder an den Browser
  gegeben. Backups enthalten standardmäßig keine Gateway-Secrets, aber
  LoRaWAN-Schlüssel; die UI weist darauf hin.
- SSRF-Grenze: nur `http`/`https`, keine URL-Credentials, kein Redirect-Follow.
- Empfehlung im README: Bei Zugriff über unsichere Netze Reverse Proxy mit TLS.

## 9. Installer-Verhalten

### Host (`install/loradeck.sh`)

1. Root-, Proxmox- (`pct`, `pveam`, `pvesh`, `/etc/pve`) Prüfung.
2. CT-ID: `pvesh get /cluster/nextid`, sofern nicht `--ctid`.
3. Existiert die ID: gleicher Hostname `loradeck` → Update-Modus (Code/Unit
   aktualisieren, DB/Secret/Admin-Passwort behalten); fremder Hostname →
   Abbruch, außer `--force`.
4. Debian-12-Template sicherstellen, Storage automatisch ermitteln.
5. Container erstellen: `--unprivileged 1 --onboot 1`, DHCP, 2 vCPU,
   2048 MB RAM, 8 GB Disk, Beschreibung „LoRaDeck – Awaro Gateway Monitor“.
6. Netz/DNS abwarten (max. 120 s), Inner-Script per `pct push` übertragen,
   im Container ausführen.
7. Verifikation vom Host: `systemctl is-active`, HTTP-Check auf `/healthz`.
8. Ausgabe: URL, CT-ID, Hostname, Admin-Passwort (nur bei Erstinstallation),
   Update-/Log-/Entfern-Kommandos.

Optionen: `--ctid --hostname --cores --ram --disk --storage
--template-storage --bridge --port --admin-password --gateway-url
--gateway-auth --poll-interval --repo --ref --force --yes --debug -h`.

Fehlerbehandlung: `set -euo pipefail`, ERR-Trap mit Exit-Code, Zeile,
Kommando, Container-Status, letzte Logzeilen, `journalctl`, offene Ports;
vollständiges Log unter `/var/log/loradeck-install.log`; `--debug` aktiviert
`bash -x`.

### Container (`install/loradeck-inner.sh`)

1. `apt-get update`, Installation von `ca-certificates curl git openssl
   python3 python3-venv python3-pip sqlite3 ufw jq nodejs npm`.
2. Systembenutzer `loradeck`, Verzeichnisse `/opt/loradeck`,
   `/var/lib/loradeck`, `/etc/loradeck`.
3. Repo klonen, App/Web/Unit kopieren (Update überschreibt Code, nicht Daten).
4. `npm ci && npm run build` im Web-Verzeichnis.
5. venv anlegen, `pip install -r requirements.txt`.
6. Konfiguration schreiben; bei Update Secret/Hash/Gateway-Auth erhalten.
7. DB initialisieren; Standard-Settings aus Env übernehmen.
8. Unit aus Template rendern, `daemon-reload`, `enable`, `restart`.
9. ufw: Port nur aus RFC1918; bei fehlenden Rechten Warnung statt Abbruch.
10. Healthcheck mit Retry; bei Fehler vollständige Diagnose.

## 10. UI

- **Look:** dunkles, redaktionelles Interface mit hellem Modus; tiefes Navy,
  Elektroblau/Cyan als Akzent, Monospace für Messwerte und DevEUIs,
  großzügiger Weißraum, klare Karten, keine externen Fonts.
- **Login:** Karte mit Benutzername/Passwort; danach die App-Shell.
- **Übersicht:** Status-Hero (online/offline, URL, letzter Poll), Kennzahlen
  (Firmware, Uptime, Heap, RSSI, Sensoren), Sparklines, Ereignisliste,
  Refresh-Button, Auto-Refresh alle 15 s.
- **Sensoren:** Tabelle mit Suche, Status-Badges, Hinweis auf Messwerte unter
  `/lns` bzw. MQTT/Home Assistant.
- **Integrationen:** Hooks-Tabelle und Decoder-Inventar (Engines, Modelle,
  eigene Tabellen mit Spec).
- **Firmware:** aktuelle Version, Hardware, Kanal, veröffentlichte Versionen,
  Update-Verfügbarkeit, Check-Button, Installationshinweis per CLI.
- **Backups:** Erzeugen, Liste mit Zeit/Größe/SHA-256, Download, Löschen,
  Sicherheitshinweis.
- **Einstellungen:** Gateway-URL, Poll-Intervall, Auth-Status, Version.
- **Zustände:** Lade-Skeleton, leere Liste, Fehlerbanner, 404-Seite.
- **A11y:** Labels, sichtbarer Fokus, ausreichende Kontraste, Tastaturbedienung.

## 11. Home Assistant und Sensoren

LoRaDeck ist **kein** Datenhub. Für Messwerte und Home-Assistant-Entitäten
bleibt die native Awaro-Integration (MQTT + HA Auto Discovery) der richtige
Weg. Das README dokumentiert:

- Awaro MQTT-Integration einrichten, HA MQTT-Broker eintragen, Auto Discovery
  aktivieren.
- Beispiel-Topic und HA-`mqtt`-Sensor.
- **Hager TG563A** (Sieben-S): EN14604, EU868, ca. 39,90 € inkl. MwSt.
  (iot-shop.de, Stand 2026-11); Payload-Decoder
  `github.com/modrisb/tg563a-payload-decoder`; 5-Byte-Tages- und
  35-Byte-Wochenframe auf fPort 1. Awaro hat keinen eingebauten Decoder.
  `smokeAlarm` ist **Bit 0 von Byte 4**; die Awaro-Decoder-Tabelle kann keine
  Bitfelder, daher `status:u8@4` als Rohbyte plus HA-Template, das Bit 0
  auswertet. Kein Plug-and-play.
- **Netvox RA02A**: ca. 66 € netto (ThingPark Market) ≈ 78 € inkl. 19 % MwSt.;
  Standard-LoRaWAN-Join, proprietäre Payload. Custom-Spec
  `fire:u8@4 high:u8@5 temp:i16@6/10#°C volt:u8@3/10#V` möglich, aber
  Low-Battery-Bit 0x80 verfälscht die Spannung und Startup-Frames liefern
  Fehlwerte. Kein Plug-and-play.
- **Deltronic X10i** und **Nexelec ORIGIN/GUARD+**: Preise und Grenzen; kein
  Awaro-Decoder für Nexelec, Feueralarm wird standardmäßig nicht
  weitergeleitet.
- **Sicherheitshinweis:** LoRaWAN/Home Assistant nie als primären Brandschutz
  verwenden; der lokale 85-dB-Alarm bleibt primär.

## 12. Verifikation

- `bash -n` und `shellcheck` für beide Installer und Testskripte.
- `pytest app/tests` gegen temporäre SQLite-DB und `httpx.MockTransport`
  (Health, Session, Login, Auth-Schutz, Settings-Validierung, Poller,
  Sensoren, Events, Backups, Firmware-Check, SPA-Fallback).
- `npm test` (Format-Helfer) und `npm run build` (TypeScript + Vite).
- `tests/local-smoke.sh`: Fake-Gateway starten, LoRaDeck lokal mit Temp-DB
  starten, Health/Login/Overview/Refresh/Sensors/Backup per curl prüfen.
- `tests/reboot-test.sh`: auf dem Proxmox-Host Installation prüfen, CT
  rebooten, auf Service und HTTP warten, Ergebnis nach
  `docs/test-evidence.md` schreiben.
- Ein echter Proxmox-/Hardware-Test ist in der Entwicklungsumgebung nicht
  möglich; Skripte und lokale Tests werden ausgeführt, der Host-Test wird
  dokumentiert und kann vom Betreiber reproduziert werden.

## 13. Betrieb

- Update: Installer erneut mit `--ctid <ID>` ausführen.
- Deinstallation: `pct stop <ID> && pct destroy <ID> --purge`.
- Admin-Passwort zurücksetzen: Installer mit `--ctid <ID> --admin-password 'neu'`.
- Gateway-Zugang ändern: UI (URL, Intervall) oder Installer (`--gateway-auth`).
- Logs: `journalctl -u loradeck -f`.
- Backup: `/var/lib/loradeck/loradeck.db`, `/var/lib/loradeck/backups/` und
  `/etc/loradeck/config.env`.

## 14. Grenzen und Risiken

- Die dokumentierte Gateway-API liefert **keine** Uplink-/Messwert-Historie.
  LoRaDeck kann daher Sensor-Health und FCnt, aber keine Temperaturen oder
  Rauchmelder-Messwerte anzeigen.
- Firmware-/API-Felder können sich mit Gateway-Updates ändern; der Client
  toleriert fehlende Felder und zeigt leere Werte statt abzustürzen.
- Ein Gateway-Ausfall macht die Verlaufsdaten nicht unbrauchbar: der letzte
  Stand und die Ereignisse bleiben sichtbar.
- Ohne erreichbares Gateway ist die App weiterhin gesund (`/healthz` 200),
  solange die lokale DB funktioniert.
