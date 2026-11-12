export type Tone = "ok" | "warn" | "danger" | "muted" | "neutral";

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatUptime(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) {
    return "—";
  }
  const total = Math.max(0, Math.floor(seconds));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (days > 0) {
    return `${days} T ${String(hours).padStart(2, "0")} h`;
  }
  if (hours > 0) {
    return `${hours} h ${String(minutes).padStart(2, "0")} min`;
  }
  return `${minutes} min`;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes)) {
    return "—";
  }
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${bytes} B`;
}

export function formatRssi(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "—";
  }
  return `${value} dBm`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "—";
  }
  return `${Math.round(value)} %`;
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "—";
  }
  return new Intl.NumberFormat("de-DE").format(value);
}

export function statusTone(status: string | null | undefined): Tone {
  switch ((status ?? "").toLowerCase()) {
    case "active":
    case "online":
    case "ok":
    case "ready":
      return "ok";
    case "never":
    case "inactive":
    case "offline":
      return "danger";
    case "warning":
    case "warn":
      return "warn";
    default:
      return status ? "neutral" : "muted";
  }
}

export function statusLabel(status: string | null | undefined): string {
  const normalized = (status ?? "").toLowerCase();
  switch (normalized) {
    case "active":
      return "Aktiv";
    case "inactive":
      return "Inaktiv";
    case "never":
      return "Nie gesehen";
    case "online":
      return "Online";
    case "offline":
      return "Offline";
    default:
      return status || "Unbekannt";
  }
}

export function eventTone(kind: string): Tone {
  switch (kind) {
    case "online":
      return "ok";
    case "offline":
      return "danger";
    case "firmware":
    case "sensor_status":
      return "warn";
    case "sensor_new":
      return "neutral";
    default:
      return "muted";
  }
}

export function eventLabel(kind: string): string {
  switch (kind) {
    case "online":
      return "Online";
    case "offline":
      return "Offline";
    case "firmware":
      return "Firmware";
    case "sensor_new":
      return "Neuer Sensor";
    case "sensor_status":
      return "Sensor-Status";
    case "backup":
      return "Backup";
    case "settings":
      return "Einstellung";
    default:
      return kind;
  }
}
