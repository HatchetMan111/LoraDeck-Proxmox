from __future__ import annotations

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
