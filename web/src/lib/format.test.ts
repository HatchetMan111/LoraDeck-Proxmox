import { describe, expect, it } from "vitest";
import {
  eventLabel,
  eventTone,
  formatBytes,
  formatNumber,
  formatRssi,
  formatUptime,
  statusLabel,
  statusTone,
} from "./format";

describe("formatUptime", () => {
  it("renders days and hours", () => {
    expect(formatUptime(90061)).toBe("1 T 01 h");
  });

  it("renders hours and minutes", () => {
    expect(formatUptime(3723)).toBe("1 h 02 min");
  });

  it("renders minutes", () => {
    expect(formatUptime(125)).toBe("2 min");
  });

  it("handles missing values", () => {
    expect(formatUptime(null)).toBe("—");
    expect(formatUptime(Number.NaN)).toBe("—");
  });
});

describe("formatBytes", () => {
  it("scales units", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });

  it("handles missing values", () => {
    expect(formatBytes(null)).toBe("—");
  });
});

describe("formatters", () => {
  it("formats rssi and numbers", () => {
    expect(formatRssi(-67)).toBe("-67 dBm");
    expect(formatRssi(null)).toBe("—");
    expect(formatNumber(1234)).toBe("1.234");
  });
});

describe("status mapping", () => {
  it("maps sensor states", () => {
    expect(statusTone("active")).toBe("ok");
    expect(statusTone("never")).toBe("danger");
    expect(statusTone("")).toBe("muted");
    expect(statusLabel("active")).toBe("Aktiv");
    expect(statusLabel("never")).toBe("Nie gesehen");
    expect(statusLabel("custom")).toBe("custom");
  });

  it("maps event kinds", () => {
    expect(eventTone("online")).toBe("ok");
    expect(eventTone("offline")).toBe("danger");
    expect(eventTone("firmware")).toBe("warn");
    expect(eventLabel("sensor_new")).toBe("Neuer Sensor");
    expect(eventLabel("unbekannt")).toBe("unbekannt");
  });
});
