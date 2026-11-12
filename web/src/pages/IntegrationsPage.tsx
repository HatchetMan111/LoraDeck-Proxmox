import { useEffect, useState } from "react";
import ErrorBanner from "../components/ErrorBanner";
import LoadingPanel from "../components/LoadingPanel";
import StatusPill from "../components/StatusPill";
import { errorMessage, getIntegrations } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { Integrations } from "../types";

const engineNames = [
  "Cayenne",
  "Milesight",
  "Elsys",
  "SenseCAP",
  "Browan",
  "Vicki",
  "FurgoNode",
];

function BoolPill({ value }: { value: boolean | null }) {
  if (value === null || value === undefined) {
    return <StatusPill tone="muted">Unbekannt</StatusPill>;
  }
  return (
    <StatusPill tone={value ? "ok" : "muted"}>
      {value ? "Aktiv" : "Inaktiv"}
    </StatusPill>
  );
}

export default function IntegrationsPage() {
  const [data, setData] = useState<Integrations | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getIntegrations()
      .then(setData)
      .catch((caught) => setError(errorMessage(caught)));
  }, []);

  if (!data) {
    return error ? <ErrorBanner message={error} /> : <LoadingPanel />;
  }

  const engines = data.builtins.filter((name) =>
    engineNames.some((engine) => name.toLowerCase().includes(engine.toLowerCase())),
  );
  const others = data.builtins.filter((name) => !engines.includes(name));

  return (
    <div className="stack">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Netzwerkserver</p>
          <h1 className="page-title">Integrationen</h1>
          <p className="page-subtitle">
            LNS-Modus, Hooks und Decoder des Gateways.
          </p>
        </div>
        <span className="muted small">
          Stand: {formatDateTime(data.updated_at)}
        </span>
      </section>

      <ErrorBanner message={error} />

      <section className="stat-grid stat-grid-compact">
        <div className="stat-card">
          <span className="stat-label">LNS-Modus</span>
          <strong className="stat-value">{data.mode || "—"}</strong>
          <span className="stat-hint">Konfiguration am Gateway</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">ADR</span>
          <strong className="stat-value">
            <BoolPill value={data.adr} />
          </strong>
          <span className="stat-hint">Adaptive Data Rate</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">USB</span>
          <strong className="stat-value">
            <BoolPill value={data.usb} />
          </strong>
          <span className="stat-hint">Serieller Zugang</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Relay</span>
          <strong className="stat-value">
            <BoolPill value={data.relay} />
          </strong>
          <span className="stat-hint">LoRaWAN Relay</span>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Hooks</h2>
          <span className="muted small">{data.hooks.length} aktiv</span>
        </div>
        {data.hooks.length === 0 ? (
          <p className="muted">Keine Hooks konfiguriert.</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Typ</th>
                  <th>Ziel</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.hooks.map((hook) => (
                  <tr key={`${hook.name}-${hook.url}`}>
                    <td>
                      <strong>{hook.name || "—"}</strong>
                    </td>
                    <td>{hook.type || "—"}</td>
                    <td className="mono break">{hook.url || "—"}</td>
                    <td>{hook.smsg || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Decoder</h2>
          <span className="muted small">
            {data.codecs.length} eigene · {data.builtins.length} eingebaut
          </span>
        </div>

        <h3 className="subheading">Eingebaute Engines</h3>
        <div className="chip-row">
          {engines.map((name) => (
            <span key={name} className="chip">
              {name}
            </span>
          ))}
        </div>

        {others.length > 0 ? (
          <>
            <h3 className="subheading">Weitere eingebaute Decoder</h3>
            <div className="chip-row">
              {others.map((name) => (
                <span key={name} className="chip">
                  {name}
                </span>
              ))}
            </div>
          </>
        ) : null}

        <h3 className="subheading">Eigene Codecs</h3>
        {data.codecs.length === 0 ? (
          <p className="muted">
            Keine eigenen Codecs. Eigene Decoder lassen sich am Gateway über die
            Awaro-CLI pflegen.
          </p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Modell</th>
                  <th>Spezifikation</th>
                </tr>
              </thead>
              <tbody>
                {data.codecs.map((codec) => (
                  <tr key={codec.model}>
                    <td>
                      <strong>{codec.model}</strong>
                    </td>
                    <td className="mono break">{codec.spec}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="muted small">
        LoRaDeck ist kein MQTT-Broker. Für Home Assistant und Messwerte nutzt du
        die native MQTT-Integration des Awaro-Gateways.
      </p>
    </div>
  );
}
