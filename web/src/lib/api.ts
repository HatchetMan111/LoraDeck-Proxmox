import type {
  Backup,
  EventItem,
  Firmware,
  Integrations,
  Overview,
  RefreshResult,
  Sample,
  Sensor,
  Session,
  Settings,
  SettingsInput,
} from "../types";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/login") {
      window.dispatchEvent(new Event("loradeck:unauthorized"));
    }
    let message = `Anfrage fehlgeschlagen (HTTP ${response.status})`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (body.detail !== undefined) {
        message = JSON.stringify(body.detail);
      }
    } catch {
      // keep the generic message
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unbekannter Fehler";
}

export function getSession(): Promise<Session> {
  return request<Session>("/api/session");
}

export function login(username: string, password: string): Promise<Session> {
  return request<Session>("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout(): Promise<void> {
  return request<void>("/api/logout", { method: "POST" });
}

export function getOverview(): Promise<Overview> {
  return request<Overview>("/api/overview");
}

export function getSamples(limit = 120): Promise<Sample[]> {
  return request<Sample[]>(`/api/samples?limit=${limit}`);
}

export function getSensors(): Promise<Sensor[]> {
  return request<Sensor[]>("/api/sensors");
}

export function getIntegrations(): Promise<Integrations> {
  return request<Integrations>("/api/integrations");
}

export function getEvents(limit = 50): Promise<EventItem[]> {
  return request<EventItem[]>(`/api/events?limit=${limit}`);
}

export function refreshGateway(): Promise<RefreshResult> {
  return request<RefreshResult>("/api/gateway/refresh", { method: "POST" });
}

export function getFirmware(): Promise<Firmware> {
  return request<Firmware>("/api/firmware");
}

export function checkFirmware(): Promise<Firmware> {
  return request<Firmware>("/api/firmware/check", { method: "POST" });
}

export function listBackups(): Promise<Backup[]> {
  return request<Backup[]>("/api/backups");
}

export function createBackup(): Promise<Backup> {
  return request<Backup>("/api/backups", { method: "POST" });
}

export function deleteBackup(id: number): Promise<void> {
  return request<void>(`/api/backups/${id}`, { method: "DELETE" });
}

export function backupDownloadUrl(id: number): string {
  return `/api/backups/${id}/download`;
}

export function getSettings(): Promise<Settings> {
  return request<Settings>("/api/settings");
}

export function updateSettings(input: SettingsInput): Promise<Settings> {
  return request<Settings>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(input),
  });
}
