export interface Session {
  authenticated: boolean;
  username: string | null;
}

export interface Sample {
  id: number;
  ts: string;
  online: boolean;
  fw: string;
  hw: string;
  uptime: number | null;
  heap: number | null;
  ip: string;
  ssid: string;
  rssi: number | null;
  mode: string;
  ns_ready: boolean | null;
  devices: number | null;
  error: string;
}

export interface Sensor {
  id: number;
  dev_id: string;
  name: string;
  grp: string;
  decoder: string;
  cls: string;
  fcnt: number | null;
  status: string;
  first_seen: string;
  last_seen: string;
  updated_at: string;
}

export interface EventItem {
  id: number;
  ts: string;
  kind: string;
  message: string;
}

export interface Hook {
  name: string;
  type: string;
  url: string;
  smsg: string;
}

export interface Codec {
  model: string;
  spec: string;
}

export interface Counts {
  sensors: number;
  events: number;
  backups: number;
  integrations: number;
  decoders: number;
  builtin_decoders: number;
}

export interface Overview {
  configured: boolean;
  auth_configured: boolean;
  gateway_url: string;
  poll_interval: number;
  poll_enabled: boolean;
  last_poll: string;
  last_error: string;
  sample: Sample | null;
  counts: Counts;
  events: EventItem[];
  version: string;
}

export interface Integrations {
  mode: string;
  adr: boolean | null;
  usb: boolean | null;
  relay: boolean | null;
  hooks: Hook[];
  codecs: Codec[];
  builtins: string[];
  updated_at: string;
}

export interface Firmware {
  cur?: string;
  hw?: string;
  url?: string;
  list?: string[];
  avail?: string;
  checked?: number | null;
  err?: string;
}

export interface Backup {
  id: number;
  ts: string;
  filename: string;
  kind: string;
  size: number;
  sha256: string;
}

export interface Settings {
  gateway_url: string;
  poll_interval: number;
  auth_configured: boolean;
  poll_enabled: boolean;
  version: string;
}

export interface SettingsInput {
  gateway_url: string;
  poll_interval: number;
}

export interface RefreshResult {
  ok: boolean;
  ts: string;
  devices: number;
}
