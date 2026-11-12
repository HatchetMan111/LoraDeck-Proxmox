# LoRaDeck

LoRaDeck ist ein lokaler, inoffizieller Begleiter für **Awaro-LoRaWAN-Gateways**.
Die App läuft in einem schlanken Debian-LXC auf Proxmox VE, liest die
Gateway-HTTP-API und zeigt Status, Sensoren, Integrationen, Firmware-Kanal und
Backups in einer aufgeräumten Web-UI.

> LoRaDeck ist ein Community-Projekt und gehört nicht zu Furgo/Awaro. „Awaro“
> wird nur beschreibend verwendet. Es werden keine Herstellerlogos oder
> proprietären Bestandteile mitgeliefert.

## Funktionen

- **Gateway-Übersicht:** Online-Status, Firmware, Hardware, Uptime, freier Heap,
  WLAN-Signal, LNS-Modus und Netzwerkserver-Bereitschaft.
- **Verlauf:** kleine Sparklines für RSSI, Heap und Uptime aus den gespeicherten
  Polls. Es werden **keine Messwerte** gespeichert.
- **Sensoren:** Name, DevEUI, Gruppe, Decoder, Klasse, FCnt und Status aus der
  Gateway-API; Erst- und Letzt-Poll-Zeitstempel aus LoRaDeck.
- **Integrationen:** LNS-Modus, ADR, USB/Relay, Hooks, eingebaute Decoder und
  eigene Codecs.
- **Firmware:** Update-Prüfung über die Gateway-API. Installation bleibt bewusst
  bei der Awaro-CLI.
- **Backups:** Gateway-Konfiguration **ohne Secrets** plus LoRaWAN-Export
  (enthält Sensorschlüssel) als JSON, mit SHA-256 und Download.
- **Ereignisse:** Online/Offline, Firmware-Wechsel, neue Sensoren und
  Statuswechsel.
- **Sicherheit:** Admin-Login mit scrypt, HMAC-Session-Cookie, LAN-only,
  restriktive systemd-Unit, Gateway-Zugangsdaten nur in `/etc/loradeck/config.env`.

## Was LoRaDeck nicht ist

- **Kein Datenhub und kein MQTT-Broker.** Für Home Assistant und Messwerte
  nutzt du die native MQTT-Integration des Awaro-Gateways.
- **Keine Messwert-Historie.** Die dokumentierte Gateway-API liefert keine
  Uplink-Historie. LoRaDeck zeigt Metadaten, keine Temperatur-/Feuchte-Charts.
- **Kein Sensor-Pairing und keine Decoder-Verwaltung.** Sensoren werden im
  Awaro-Gateway registriert; LoRaDeck liest sie nur.
- **Keine Downlinks, kein USB-/Serial-Zugriff, kein Firmware-Install.**
- **Kein Multi-Gateway.** Eine Instanz betreut ein Gateway.

## Installation

Auf einem Proxmox-VE-Host als root:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/HatchetMan111/loradeck-proxmox/main/install/loradeck.sh)"
```

Der Installer legt einen unprivilegierten Debian-12-LXC an (Standard: 2 vCPU,
2048 MB RAM, 8 GB Disk, DHCP, `onboot: 1`), baut Frontend und Backend, richtet
systemd und ufw ein und startet den Dienst auf Port `8080`.

### Optionen

| Option | Bedeutung |
| --- | --- |
| `--ctid ID` | CT-ID (Standard: nächste freie) |
| `--hostname NAME` | Container-Hostname (Standard: `loradeck`) |
| `--cores N` / `--ram MB` / `--disk GB` | Ressourcen |
| `--storage NAME` | Storage für die Disk |
| `--bridge NAME` | Linux-Bridge (Standard: `vmbr0`) |
| `--port N` | Web-Port (Standard: `8080`) |
| `--admin-password PW` | Admin-Passwort setzen |
| `--gateway-url URL` | Gateway-URL vorbelegen |
| `--gateway-auth USER:PASS` | Gateway-Basic-Auth setzen |
| `--repo URL` / `--ref REF` | Git-Quelle |
| `--force` | Fremden Container mit dieser ID entfernen |
| `--yes` | nicht-interaktiv |
| `--debug` | `bash -x` und erweiterte Diagnose |

Beispiel mit fester CT-ID und vorbelegtem Gateway:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/HatchetMan111/loradeck-proxmox/main/install/loradeck.sh)" -- \
  --ctid 120 --gateway-url http://192.168.1.40
```

### Erster Login

Der Installer gibt das Admin-Passwort einmalig aus. Wenn kein Terminal
verfügbar ist, liegt es unter `/root/loradeck-admin-password` auf dem
Proxmox-Host. Benutzer ist `admin`.

Passwort zurücksetzen (Installation wird erneut ausgeführt):

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/HatchetMan111/loradeck-proxmox/main/install/loradeck.sh)" -- \
  --ctid <ID> --admin-password 'NEUES-PASSWORT'
```

## Gateway verbinden

1. Web-UI öffnen: `http://<CT-IP>:8080`
2. Unter **Einstellungen** die Gateway-URL eintragen, z. B.
   `http://192.168.1.40`.
3. Poll-Intervall wählen (15–3600 Sekunden).
4. Auf der Übersicht **Jetzt aktualisieren** klicken.

Die Gateway-URL und das Intervall liegen in SQLite und gelten sofort. Ein
Neustart ist nicht nötig.

### Gateway mit Basic Auth

Falls die Gateway-API durch HTTP Basic Auth geschützt ist, werden die
Zugangsdaten ausschließlich in der root-eigenen Konfiguration hinterlegt:

```bash
pct exec <ID> -- editor /etc/loradeck/config.env
# LORADECK_GATEWAY_AUTH='monitor:geheim'
pct exec <ID> -- systemctl restart loradeck
```

Die UI zeigt nur, **ob** Zugangsdaten konfiguriert sind – niemals die Werte.

## Home Assistant

LoRaDeck ist kein Broker. Die empfohlene Kette ist:

```text
Awaro-Gateway --(MQTT-Hook)--> dein MQTT-Broker --> Home Assistant
```

Den MQTT-Hook richtest du am Gateway ein (Host, Port, Topic). Home Assistant
abonniert das Topic und liest die vom Gateway bereits dekodierten Felder.
LoRaDeck kann parallel laufen, ist aber nicht Teil dieser Kette.

## Sensor-Kompatibilität

LoRaDeck ist die Monitoring-Oberfläche. **Sensoren werden am Awaro-Gateway
registriert**, nicht in LoRaDeck. Entscheidend ist, ob das Gateway die Payload
dekodieren kann. Es gibt drei Stufen:

| Stufe | Was du tun musst | Aufwand |
| --- | --- | --- |
| **1. Eingebauter Decoder** | Modell beim Anlegen des Sensors in Awaro auswählen | ~1 Minute |
| **2. Tabellen-Codec** | JSON im Awaro-Reiter „Decoders“ importieren, echten Uplink-Frame testen, Sensor zuweisen | 10–30 Minuten |
| **3. Nur externer Netzwerkserver** | TTN/ChirpStack davor; LoRaDeck sieht dann nur die Gateway-Health, keine Sensordaten | nicht nativ |

Awaro 3.6.6 (EU868, LoRaWAN 1.0.4, Class A/C, OTAA/ABP, bis 128 Sensoren) bringt
**47 Decoder-Einträge** mit. Die genaue Liste im Decoder-Dropdown des Gateways
ist maßgeblich; die folgenden Tabellen sind eine Orientierung.

### Vor dem Kauf: 6-Punkte-Check

1. **EU868** – kein US915/AS923/CN470. Die Frequenz ist bei den meisten Sensoren
   fest ab Werk.
2. **OTAA** bevorzugt; ABP funktioniert ebenfalls.
3. **Class A oder C** – Class B wird nicht unterstützt.
4. **Payload dokumentiert** oder ein Decoder/Codec existiert bereits.
5. **Join-Taste erreichbar** und Batterie eingelegt.
6. Bei sicherheitsrelevanter Sensorik: **lokaler Alarm** muss primär bleiben.

### Sofort einsatzbereit: eingebaute Decoder

| Kategorie | Beispiele (eines reicht) | Decoder | Hinweis |
| --- | --- | --- | --- |
| Temperatur/Feuchte | Dragino S31-LB, LHT52, LHT65N; Milesight EM300-TH, EM320-TH; Elsys ERS/EMS/ELT (passendes Modell); SenseCAP S21xx (passendes Modell) | `Dragino …`, `Milesight`, `Elsys`, `SenseCAP` | Der klassische Einstieg; LHT65N kann zusätzlich DS18B20, ADC, Zähler oder Türkontakt |
| Luftqualität (CO₂/TVOC/PM) | Milesight AM103/AM308, EM500-CO2; Elsys ERS CO2; SenseCAP S21xx | `Milesight`, `Elsys`, `SenseCAP` | Milesight liefert CO₂, TVOC, PM2,5, PM10, Temperatur und Feuchte in einem Gerät |
| Tür/Fenster | Dragino LDS02; Milesight WS301; Elsys EMS Door; Browan Door | `Dragino …`, `Milesight`, `Elsys`, `Browan` | LDS02 meldet zusätzlich Öffnungszähler und letzte Öffnungsdauer |
| Wasserleck | Dragino LWL02; Milesight WS303; Browan Leak | `Dragino …`, `Milesight`, `Browan` | LWL02 sendet im Leckfall alle 10 Minuten |
| Bewegung/Präsenz | Milesight WS202; Browan Motion; Elsys ERS Eye | `Milesight`, `Browan`, `Elsys` | WS202 kombiniert PIR und Helligkeit |
| Helligkeit | Milesight EM500-LGT, WS202; Elsys ERS/EMS mit Lichtsensor | `Milesight`, `Elsys` | Für tageslichtabhängige Automationen |
| Bodenfeuchte/EC | Milesight EM500-SMTC | `Milesight` | Bodenfeuchte, EC und Temperatur; Dragino LSE01 siehe Tabellen-Codec |
| Distanz/Füllstand | Milesight EM310-UDL, EM500-UDL, EM500-SWL | `Milesight` | Ultraschall für Tank, Silo, Parkplatz; EM500-SWL für Wasserstand |
| Druck | Milesight EM500-PP | `Milesight` | Differenz-/Absolutdruck; Dragino PS-LB siehe Tabellen-Codec |
| Zähler/Puls/Energie | Dragino CPL03-LB; Milesight WS523 | `Dragino …`, `Milesight` | CPL03-LB: 3 Eingänge, Pulszähler, Kontaktstatus; WS523: Steckdose mit Verbrauchsmessung |
| Ventil/Heizung | MClimate Vicki; Milesight WT101 | `Vicki`, `Milesight` | Heizkörperthermostate; Downlinks nur mit Class C sofort |
| Taster | Milesight WS101; Browan Button | `Milesight`, `Browan` | Kurz/lang/doppelt je nach Modell |
| GPS/Tracker | Dragino TrackerD; Browan Locator | `TrackerD`, `Browan` | TrackerD liefert GPS, Temperatur und Batterie |
| Wetterstation | SenseCAP S2120 | `SenseCAP` | 8-in-1: Temperatur, Feuchte, Wind, Regen, Licht, UV, Druck |
| pH | Dragino LSPH01 | `Dragino …` | Für Wasser/Erde; Sonde regelmäßig kalibrieren |
| I/O / Multi-Modus | Dragino CPL03-LB, SN50v3-LB | `Dragino …` | SN50v3 hat einen Decoder **pro Arbeitsmodus**; Modus beim Anlegen passend wählen |
| Generisch | jedes Gerät mit **Cayenne LPP** | `cayenne` | Herstellerunabhängig; Felder werden automatisch erkannt |

Zusätzlich eingebaut: **FurgoNode/Hautense** (eigene Furgo-Sensoren) und die
**Dragino-Kernmodelle** LHT52, LHT65N, S31-LB, CPL03-LB, T68DL, TrackerD und
SN50v3-LB. Die Dragino-Liste umfasst rund 40 Referenzen für Tür, Leck, Distanz,
Boden, pH, CO₂, Temperatur, Druck, Neigung, Stromzangen, Ventil-/I/O-Controller
und GPS-Tracker.

**Verifizierte Modelllisten (Auswahl):**

- **Milesight:** AM103/AM103L, AM307/AM308/AM319, EM300-TH, EM300-SLD,
  EM300-MCS, EM310-UDL, EM320-TH, EM500-CO2, EM500-LGT, EM500-PT100,
  EM500-SMTC, EM500-SWL, EM500-UDL, EM500-PP, WS101, WS202, WS301, WS303,
  WS523, WT101.
- **Elsys:** ein Decoder für die ERS/EMS/ELT-Serie, z. B. ERS Lite, ERS CO2,
  ERS Eye, EMS Door, EMS Desk, ELT-2.
- **SenseCAP:** S2101 bis S2108 sowie die 8-in-1-Wetterstation S2120.
- **Browan/Tabs:** Tür, Bewegung, Raumklima/Luftqualität, Licht, Schall, Leck,
  Locator und Taster.
- **Dragino:** die eingebauten Kernmodelle oben plus rund 30 weitere
  Referenzen; die genaue Auswahl steht im Decoder-Dropdown des Gateways.

### Mit importiertem Tabellen-Codec

Diese Sensoren sind nicht überall eingebaut, lassen sich aber mit einem kurzen
JSON-Codec nachrüsten. Die Specs sind gegen die offiziellen Herstellerdecoder
geprüft und können direkt in Awaro importiert werden.

| Modell | Codec-Spec | Hinweis |
| --- | --- | --- |
| **Hager TG563A** | `status:u8@4` + HA-Template | Rauchmelder; Alarm ist Bit 0 von Byte 4, deshalb als ganzes Byte lesen |
| **Netvox RA02A** | `fire:u8@4 high:u8@5 temp:i16@6/10#°C volt:u8@3/10#V` | Rauchmelder; Low-Battery-Bit `0x80` verfälscht Volt, Startup-Frames liefern Müll |
| Dragino LAQ4 | `bat:u16@0/1000#V tvoc:u16@3#ppb co2:u16@5#ppm temp:i16@7/10#°C hum:u16@9/10#%` | Luftqualität; MOD=31-Antworten und Kalibrierframes nicht als Messwerte interpretieren |
| Dragino LSE01 | `bat:u16@0/1000#V water_SOIL:u16@4/100#% conduct_SOIL:u16@8#µS/cm` | Bodenfeuchte/EC; gilt für den Default-Modus MOD=0 |
| Dragino LDDS75 | `bat:u16@0/1000#V distance:u16@2#mm interrupt:u8@4 temp:i16@5/10#°C sensor_flag:u8@7` | Ultraschall; 0 mm/20 mm sind Fehlerwerte, kein gültiger Abstand |
| Dragino PS-LB | `bat:u16@0/1000#V idc_in:u16@4/1000#mA vdc_in:u16@6/1000#V pulses:u32@9` | Druck/4–20 mA; abgeleitete Werte (Wassertiefe etc.) in HA berechnen |

Weitere fertige Codecs und Importdateien:
[lorawan2mqtt/codecs](https://github.com/lorawan2mqtt/lorawan2mqtt/tree/main/codecs)
und die offiziellen
[Dragino-Decoder](https://github.com/dragino/dragino-end-node-decoder).

### Eigenen Codec schreiben

Im Awaro-Reiter **Decoders** legst du Name, Felder und Testframe an. Firmware
3.6.6 erlaubt **8 eigene Codecs**, **24 Felder** und **511 Zeichen** pro Codec
(ältere Firmware: 159/160 Zeichen). Unterstützt werden:

- Typen `u8 i8 u16 i16 u24 i24 u32 i32 f32` (großes Ende), mit `l` für
  Little-Endian (`u16l`, `i24l`, …)
- Offset, Divisor (`/10`, `/100`, `/1000`), Offset nach der Division (`+`/`-`)
  und Einheit (`#°C`, `#%`, `#V`, …)
- FPort pro Feld, damit Service-Frames nicht als Messwerte erscheinen

**Nicht** abbildbar sind Bitfelder, TLV-/selbstbeschreibende Frames, variable
Layouts je nach Modusbyte, Strings und bedingte Decoder. Dafür braucht es einen
eingebauten Decoder (Milesight, Elsys, SenseCAP, Browan, Dragino) oder einen
externen Netzwerkserver. Teste immer einen **echten Uplink-Frame**, keinen aus dem
Datenblatt zusammengebaute.

### Nicht nativ unterstützt

| Modell | Grund | Alternative |
| --- | --- | --- |
| Nexelec ORIGIN / GUARD+ | kein Awaro-Decoder; komplexe, bedingte Payload | externer Netzwerkserver mit Herstellerdecoder |
| Deltronic X10i | kein Awaro-Decoder | externer Netzwerkserver |
| Milesight VS121 | AI-Personenzähler, vom eingebauten Milesight-Decoder nicht abgedeckt | externer Netzwerkserver |
| Sensoren mit Class B | Awaro unterstützt Class A/C | anderes Modell wählen |
| Exotische TLV-/Herstellerformate | nicht als Tabelle abbildbar | eingebauten Decoder prüfen oder externer NS |

### Sensor verbinden: der Ablauf

1. Sensor in den Join-Modus bringen (meist langer Tastendruck; bei Dragino-LB
   oft **>3 Sekunden**).
2. In Awaro `http://<gateway>/lns` → Sensor hinzufügen: **DevEUI**, **JoinEUI**,
   **AppKey**, Class und **Decoder**.
3. Bei OTAA joinen lassen; bei ABP die Session-Keys eintragen.
4. In LoRaDeck unter **Sensoren** prüfen: Status, FCnt und letzter Poll.
5. Messwerte erscheinen über den MQTT-Hook in Home Assistant – nicht in
   LoRaDeck. LoRaDeck zeigt nur Gateway- und Sensor-Metadaten.
6. Kein Join? DevEUI/AppKey, EU868-Subband, Distanz und Batterie prüfen. Keine
   Messwerte? Decoder, FPort und Testframe prüfen:
   `awaro lns <gateway> test <decoder> <hexpayload>`.

### Empfehlungen nach Anwendungsfall

- **Einsteiger-Set:** Dragino S31-LB (Temperatur/Feuchte), LDS02 (Tür) und
  LWL02 (Leck) – alle eingebaut, günstig, EU868, OTAA.
- **Beste Abdeckung:** Milesight EM300-TH, WS301, WS303, WS202 und WS101 – ein
  Decoder für die ganze Serie, robuste Gehäuse.
- **Garten/Boden:** Milesight EM500-SMTC (eingebaut) oder Dragino LSE01
  (Tabellen-Codec).
- **Tank/Silo:** Milesight EM500-SWL/UDL (eingebaut) oder Dragino LDDS75
  (Tabellen-Codec).
- **Rauch:** Hager TG563A (günstig, Codec) oder Netvox RA02A; siehe unten.
- **Luftqualität:** Milesight AM103/AM308 (eingebaut) oder Dragino LAQ4
  (Tabellen-Codec).

## Rauchmelder

**Kein Rauchmelder ist mit Awaro Plug-and-play.** Die folgende Tabelle ist eine
Momentaufnahme (Preise Stand November 2026, ohne Gewähr) und beschreibt, was mit
Awaro-Decodern praktisch möglich ist.

| Modell | Preis ca. | Awaro-Decoder | Bewertung |
| --- | --- | --- | --- |
| **Hager TG563A** | **39,90 €** | eigener Codec `status:u8@4` + HA-Template | **Empfehlung** für Bastler |
| Netvox RA02A | ~78 € inkl. MwSt. | eigener Codec `fire:u8@4 high:u8@5 temp:i16@6/10#°C volt:u8@3/10#V` | möglich, mit Einschränkungen |
| Deltronic X10i | 62,90 € | keiner | nicht empfohlen |
| Nexelec ORIGIN / GUARD+ | 59–79 € | keiner | nicht empfohlen |

### Hager TG563A

- EN14604, EU868, 10-Jahres-Batterie, 39,90 € inkl. MwSt.
- Sendet 5-Byte-Frames täglich und 35-Byte-Frames wöchentlich auf FPort 1.
- Der Alarm ist **Bit 0 von Byte 4**. Awaro-Codecs können keine Bitfelder
  abbilden. Deshalb als ganzes Byte dekodieren und in Home Assistant auswerten:

```yaml
mqtt:
  binary_sensor:
    - name: "Hager Rauchmelder"
      state_topic: "awaro/<devid>/uplink"
      value_template: "{{ 'ON' if (value_json.status | int(0)) % 2 == 1 else 'OFF' }}"
      device_class: smoke
      payload_on: "ON"
      payload_off: "OFF"
```

Das Topic und der Feldname hängen von deinem Awaro-MQTT-Hook ab – passe beides
an. Der Codec am Gateway ist `status:u8@4`.

### Netvox RA02A

- FireAlarm belegt das ganze Byte 4, daher als `fire:u8@4` abbildbar.
- Low-Battery-Bit (`0x80`) im Volt-Byte verfälscht die Spannungsanzeige.
- Startup-Frames enthalten keine gültigen Messwerte und erzeugen kurzzeitig
  Fehlwerte.
- Join läuft über Standard-LoRaWAN, die Payload ist proprietär.

### Sicherheitshinweis

LoRaWAN und Home Assistant sind **kein primärer Brandschutz**. Der lokale
85-dB-Alarm des Melders bleibt die primäre Warnung. Nutze LoRaWAN nur als
zusätzliche Information und teste jeden Melder vor dem Einsatz.

## Backup und Update

- **Backup erstellen:** Web-UI → Backups → Backup erstellen. Die Datei enthält
  die Gateway-Konfiguration ohne Secrets und den LoRaWAN-Export **mit**
  Sensorschlüsseln. Sie liegt unter `/var/lib/loradeck/backups` (Modus `0600`).
- **Update:** Installer mit derselben CT-ID erneut ausführen:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/HatchetMan111/loradeck-proxmox/main/install/loradeck.sh)" -- --ctid <ID>
```

Datenbank, Secret und Admin-Hash bleiben erhalten.

## Sicherheit

- Nur für das LAN gedacht; standardmäßig kein TLS. Veröffentliche den Port nicht
  direkt im Internet. Für Fernzugriff ein VPN verwenden.
- ufw erlaubt Port `8080` und SSH nur aus RFC1918-Netzen.
- Admin-Passwort: scrypt (N=2^14, r=8, p=1), Session-Cookie HMAC-signiert,
  `HttpOnly`, `SameSite=Lax`, TTL 12 Stunden.
- Login-Rate-Limit: 5 Fehlversuche pro 5 Minuten und Client.
- Gateway-Zugangsdaten stehen nur in `/etc/loradeck/config.env` (root, `0600`)
  und werden nie an den Browser ausgeliefert.
- Backups enthalten LoRaWAN-Schlüssel. Entsprechend schützen.

## API

Alle Admin-Endpunkte brauchen eine Session. `GET /healthz` ist offen.

| Methode | Pfad | Zweck |
| --- | --- | --- |
| `GET` | `/healthz` | Healthcheck |
| `GET` | `/api/session` | Login-Status |
| `POST` | `/api/login` / `/api/logout` | Anmeldung |
| `GET` | `/api/overview` | Übersicht inkl. letztem Sample und Ereignissen |
| `GET` | `/api/samples?limit=120` | gespeicherte Polls |
| `GET` | `/api/sensors` | Sensoren |
| `GET` | `/api/integrations` | Hooks, Decoder, LNS-Modus |
| `GET` | `/api/events?limit=50` | Ereignisse |
| `POST` | `/api/gateway/refresh` | sofortiger Poll |
| `GET` | `/api/firmware` | Firmware-Status |
| `POST` | `/api/firmware/check` | asynchrone Update-Prüfung |
| `GET`/`POST` | `/api/backups` | Backups listen/erstellen |
| `GET` | `/api/backups/{id}/download` | Backup herunterladen |
| `DELETE` | `/api/backups/{id}` | Backup löschen |
| `GET`/`PUT` | `/api/settings` | Gateway-URL und Intervall |

## Entwicklung

```bash
bash tests/api.sh
(cd web && npm ci && npm test && npm run build)
bash tests/local-smoke.sh
bash tests/static-checks.sh
```

Der Smoke-Test startet einen Fake-Awaro-Gateway
(`app/tests/fake_gateway.py`) und eine lokale Uvicorn-Instanz. Für die
Frontend-Entwicklung:

```bash
# Terminal 1
PYTHONPATH=app app/.venv/bin/python app/tests/fake_gateway.py --port 8099

# Terminal 2
cd app
LORADECK_DB=/tmp/loradeck-dev.db \
LORADECK_BACKUP_DIR=/tmp/loradeck-dev-backups \
LORADECK_SECRET=dev-secret \
LORADECK_GATEWAY_URL=http://127.0.0.1:8099 \
LORADECK_POLL_ENABLED=0 \
LORADECK_ADMIN_HASH="$(PYTHONPATH=. .venv/bin/python -c 'from loradeck.auth import hash_password; print(hash_password("dev"))')" \
.venv/bin/uvicorn loradeck.main:app --reload --port 8080

# Terminal 3
cd web && npm run dev
```

Vite proxyt `/api` und `/healthz` auf `127.0.0.1:8080`.

## Troubleshooting

| Problem | Prüfen |
| --- | --- |
| Login schlägt fehl | Benutzer `admin`, Passwort aus Installer; nach 5 Fehlversuchen 5 Minuten warten |
| Gateway nicht erreichbar | URL, Netzroute, Basic Auth, `pct exec <ID> -- journalctl -u loradeck -n 100` |
| Keine Sensoren | Join am Gateway, Decoder, FCnt; einmal **Jetzt aktualisieren** |
| Firmware-Prüfung hängt | Die Prüfung ist asynchron; LoRaDeck pollt bis zu 30 Sekunden |
| Backup schlägt fehl | Gateway-Export erreichbar? Ggf. Basic Auth in `config.env` |
| UI zeigt 404 | `web/dist` fehlt; im CT `cd /opt/loradeck/web && npm run build` |

Logs:

```bash
pct exec <ID> -- journalctl -u loradeck -f
pct exec <ID> -- tail -n 100 /var/log/loradeck-install.log
```

## Test-Evidenz

Lokale Ergebnisse und der noch offene Proxmox-Reboot-Test stehen in
[`docs/test-evidence.md`](docs/test-evidence.md).

## Lizenz

MIT – siehe [`LICENSE`](LICENSE).
