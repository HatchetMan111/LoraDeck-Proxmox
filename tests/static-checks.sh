#!/usr/bin/env bash
#
# static-checks.sh - Syntax, Shellcheck und Strukturpruefungen ohne Proxmox.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAIL=0

pass() { printf '\033[32m[OK]\033[0m    %s\n' "$*"; }
fail() { printf '\033[31m[FAIL]\033[0m  %s\n' "$*"; FAIL=1; }

changedir() { cd "$ROOT"; }
changedir

echo "== bash -n =="
while IFS= read -r script; do
  if bash -n "$script"; then
    pass "Syntax: $script"
  else
    fail "Syntax: $script"
  fi
done < <(find install tests -name '*.sh' -type f | sort)

echo
echo "== shellcheck =="
if command -v shellcheck >/dev/null 2>&1; then
  if shellcheck -x install/loradeck.sh install/loradeck-inner.sh tests/*.sh; then
    pass "shellcheck"
  else
    fail "shellcheck"
  fi
else
  echo "[SKIP] shellcheck nicht installiert"
fi

echo
echo "== systemd-Unit =="
UNIT="systemd/loradeck.service"
for pattern in \
  'Restart=always' \
  'After=network-online.target' \
  'Wants=network-online.target' \
  'ExecStart=.*--host 0.0.0.0' \
  'ReadWritePaths=/var/lib/loradeck' \
  'StateDirectory=loradeck' \
  'NoNewPrivileges=true'; do
  if grep -q -- "$pattern" "$UNIT"; then
    pass "Unit: $pattern"
  else
    fail "Unit: $pattern fehlt"
  fi
done

echo
echo "== Host-Installer =="
for pattern in \
  'pvesh get /cluster/nextid' \
  'ctid_in_use' \
  'CTID_EXPLICIT' \
  'CT_HOSTNAME="LoRaWan"' \
  '--force nur zusammen mit --ctid' \
  '--onboot 1' \
  '--unprivileged 1' \
  'set -euo pipefail' \
  'onboot: 1' \
  'loradeck-inner.sh'; do
  if grep -q -- "$pattern" install/loradeck.sh; then
    pass "Host: $pattern"
  else
    fail "Host: $pattern fehlt"
  fi
done

echo
echo "== Container-Installer =="
for pattern in \
  'systemctl enable' \
  'npm run build' \
  'python3 -m venv' \
  '/healthz' \
  'loradeck.service' \
  'wait_for_dns' \
  'APT-Versuch' \
  'LORADECK_ADMIN_HASH' \
  'LORADECK_BACKUP_DIR'; do
  if grep -q -- "$pattern" install/loradeck-inner.sh; then
    pass "Inner: $pattern"
  else
    fail "Inner: $pattern fehlt"
  fi
done

echo
echo "== Struktur =="
for file in \
  app/loradeck/main.py \
  app/requirements.txt \
  web/package-lock.json \
  web/dist/index.html \
  LICENSE; do
  if [[ -f "$file" ]]; then
    pass "Datei: $file"
  else
    fail "Datei fehlt: $file"
  fi
done

echo
echo "== README-Einzeiler =="
if grep -q 'raw.githubusercontent.com/HatchetMan111/loradeck-proxmox/main/install/loradeck.sh' README.md; then
  pass "README enthaelt Installations-Einzeiler"
else
  fail "README-Einzeiler fehlt"
fi

echo
if [[ "$FAIL" -eq 0 ]]; then
  echo "Alle statischen Pruefungen bestanden."
else
  echo "Statische Pruefungen fehlgeschlagen." >&2
  exit 1
fi
