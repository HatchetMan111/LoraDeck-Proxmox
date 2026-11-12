import { useEffect, useState } from "react";
import ErrorBanner from "../components/ErrorBanner";
import LoadingPanel from "../components/LoadingPanel";
import StatCard from "../components/StatCard";
import { checkFirmware, errorMessage, getFirmware } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { Firmware } from "../types";

function formatChecked(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (value > 1_000_000_000) {
    return formatDateTime(new Date(value * 1000).toISOString());
  }
  return String(value);
}

export default function FirmwarePage() {
  const [firmware, setFirmware] = useState<Firmware | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getFirmware()
      .then(setFirmware)
      .catch((caught) => setError(errorMessage(caught)));
  }, []);

  async function handleCheck() {
    setBusy(true);
    setError("");
    try {
      setFirmware(await checkFirmware());
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  if (!firmware) {
    return error ? <ErrorBanner message={error} /> : <LoadingPanel />;
  }

  const available = firmware.avail || "";

  return (
    <div className="stack">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Update-Kanal</p>
          <h1 className="page-title">Firmware</h1>
          <p className="page-subtitle">
            LoRaDeck prüft nur. Installiert wird über die Awaro-CLI.
          </p>
        </div>
        <button
          type="button"
          className="button button-primary"
          onClick={handleCheck}
          disabled={busy}
        >
          {busy ? "Prüfe …" : "Auf Update prüfen"}
        </button>
      </section>

      <ErrorBanner message={error} />

      {firmware.err ? (
        <div className="alert alert-error">
          Prüffehler des Gateways: {firmware.err}
        </div>
      ) : null}

      {available ? (
        <div className="alert alert-success">
          Update verfügbar: <strong>{available}</strong>
          <span className="alert-code">
            awaro update &lt;gateway&gt; --install {available}
          </span>
        </div>
      ) : firmware.checked ? (
        <div className="alert alert-success">
          Kein Update verfügbar – das Gateway ist aktuell.
        </div>
      ) : null}

      <section className="stat-grid stat-grid-compact">
        <StatCard label="Aktuell" value={firmware.cur || "—"} />
        <StatCard label="Hardware" value={firmware.hw || "—"} />
        <StatCard
          label="Verfügbar"
          value={available || "—"}
          tone={available ? "warn" : undefined}
        />
        <StatCard label="Zuletzt geprüft" value={formatChecked(firmware.checked)} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Veröffentlichungen</h2>
          <span className="muted small">Kanal: {firmware.url || "—"}</span>
        </div>
        {firmware.list && firmware.list.length > 0 ? (
          <div className="chip-row">
            {firmware.list.map((version) => (
              <span
                key={version}
                className={
                  version === firmware.cur ? "chip chip-current" : "chip"
                }
              >
                {version}
                {version === firmware.cur ? " · installiert" : ""}
              </span>
            ))}
          </div>
        ) : (
          <p className="muted">Keine veröffentlichten Versionen gemeldet.</p>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Installation</h2>
        </div>
        <p className="muted">
          Firmware-Installationen sind bewusst nicht Teil von LoRaDeck. Nutze
          die Awaro-CLI auf einem Rechner im selben Netz:
        </p>
        <pre className="code-block">
{`# Prüfen
awaro update <gateway-ip>

# Installieren
awaro update <gateway-ip> --install <version>

# Bei Anti-Brick-Sperre
awaro update <gateway-ip> --unblock`}
        </pre>
        <p className="muted small">
          Das Gateway startet während der Installation neu. Plane ein
          Wartungsfenster und prüfe vorher das Backup.
        </p>
      </section>
    </div>
  );
}
