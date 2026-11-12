import { useEffect, useState, type FormEvent } from "react";
import ErrorBanner from "../components/ErrorBanner";
import LoadingPanel from "../components/LoadingPanel";
import StatCard from "../components/StatCard";
import StatusPill from "../components/StatusPill";
import { errorMessage, getSettings, updateSettings } from "../lib/api";
import type { Settings } from "../types";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [gatewayUrl, setGatewayUrl] = useState("");
  const [interval, setIntervalValue] = useState(60);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getSettings()
      .then((data) => {
        setSettings(data);
        setGatewayUrl(data.gateway_url);
        setIntervalValue(data.poll_interval);
      })
      .catch((caught) => setError(errorMessage(caught)));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const next = await updateSettings({
        gateway_url: gatewayUrl.trim(),
        poll_interval: Number(interval),
      });
      setSettings(next);
      setGatewayUrl(next.gateway_url);
      setIntervalValue(next.poll_interval);
      setNotice("Einstellungen gespeichert.");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  if (!settings) {
    return error ? <ErrorBanner message={error} /> : <LoadingPanel />;
  }

  return (
    <div className="stack">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Konfiguration</p>
          <h1 className="page-title">Einstellungen</h1>
          <p className="page-subtitle">
            Gateway-Adresse und Poll-Intervall gelten sofort.
          </p>
        </div>
      </section>

      {notice ? <div className="alert alert-success">{notice}</div> : null}
      <ErrorBanner message={error} />

      <form className="panel settings-form" onSubmit={handleSubmit}>
        <div className="panel-heading">
          <h2>Gateway</h2>
        </div>
        <label className="field">
          <span>Gateway-URL</span>
          <input
            type="url"
            value={gatewayUrl}
            onChange={(event) => setGatewayUrl(event.target.value)}
            placeholder="http://192.168.1.40"
          />
          <small>
            Nur <code>http://</code> oder <code>https://</code>, ohne
            Zugangsdaten und ohne Pfad. Leer lassen, um die Verbindung zu
            entfernen.
          </small>
        </label>
        <label className="field">
          <span>Poll-Intervall (Sekunden)</span>
          <input
            type="number"
            min={15}
            max={3600}
            value={interval}
            onChange={(event) => setIntervalValue(Number(event.target.value))}
            required
          />
          <small>Zwischen 15 und 3600 Sekunden.</small>
        </label>
        <div className="form-actions">
          <button type="submit" className="button button-primary" disabled={busy}>
            {busy ? "Speichere …" : "Speichern"}
          </button>
        </div>
      </form>

      <section className="stat-grid stat-grid-compact">
        <StatCard label="Version" value={settings.version} />
        <StatCard
          label="Hintergrund-Poller"
          value={
            <StatusPill tone={settings.poll_enabled ? "ok" : "muted"}>
              {settings.poll_enabled ? "Aktiv" : "Deaktiviert"}
            </StatusPill>
          }
          hint="Vom Installer gesetzt"
        />
        <StatCard
          label="Gateway-Auth"
          value={
            <StatusPill tone={settings.auth_configured ? "ok" : "muted"}>
              {settings.auth_configured ? "Konfiguriert" : "Keine"}
            </StatusPill>
          }
          hint="Nur über /etc/loradeck/config.env"
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Zugangsdaten</h2>
        </div>
        <p className="muted">
          Optionale Gateway-Zugangsdaten (HTTP Basic Auth) werden ausschließlich
          vom Installer in <code>/etc/loradeck/config.env</code> hinterlegt und
          nie an den Browser ausgeliefert. Änderungen dort erfordern einen
          Neustart des Dienstes.
        </p>
        <pre className="code-block">
{`# /etc/loradeck/config.env (root, 0600)
LORADECK_GATEWAY_AUTH='monitor:geheim'

sudo systemctl restart loradeck`}
        </pre>
      </section>
    </div>
  );
}
