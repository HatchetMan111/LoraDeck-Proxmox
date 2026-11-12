import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import ErrorBanner from "../components/ErrorBanner";
import LoadingPanel from "../components/LoadingPanel";
import Sparkline from "../components/Sparkline";
import StatCard from "../components/StatCard";
import StatusPill from "../components/StatusPill";
import {
  errorMessage,
  getOverview,
  getSamples,
  refreshGateway,
} from "../lib/api";
import {
  eventLabel,
  eventTone,
  formatBytes,
  formatDateTime,
  formatNumber,
  formatRssi,
  formatUptime,
} from "../lib/format";
import type { Overview, Sample } from "../types";

export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [nextOverview, nextSamples] = await Promise.all([
      getOverview(),
      getSamples(120),
    ]);
    setOverview(nextOverview);
    setSamples(nextSamples);
  }, []);

  useEffect(() => {
    let active = true;
    const tick = async () => {
      try {
        await load();
        if (active) {
          setError("");
        }
      } catch (caught) {
        if (active) {
          setError(errorMessage(caught));
        }
      }
    };
    void tick();
    const timer = window.setInterval(() => {
      void tick();
    }, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [load]);

  async function handleRefresh() {
    setBusy(true);
    setError("");
    try {
      await refreshGateway();
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  if (!overview) {
    return error ? (
      <div className="stack">
        <ErrorBanner message={error} />
        <button
          type="button"
          className="button"
          onClick={() => {
            void load().catch((caught) => setError(errorMessage(caught)));
          }}
        >
          Erneut laden
        </button>
      </div>
    ) : (
      <LoadingPanel />
    );
  }

  if (!overview.configured) {
    return (
      <EmptyState
        title="Gateway noch nicht eingerichtet"
        action={
          <Link className="button button-primary" to="/settings">
            Gateway verbinden
          </Link>
        }
      >
        Trage die Adresse deines Awaro-Gateways ein. LoRaDeck liest danach
        Status, Sensoren, Integrationen und Firmware-Informationen aus.
      </EmptyState>
    );
  }

  const sample = overview.sample;
  const online = sample?.online ?? false;
  const rssiValues = samples.map((item) => (item.online ? item.rssi : null));
  const heapValues = samples.map((item) => (item.online ? item.heap : null));
  const uptimeValues = samples.map((item) => (item.online ? item.uptime : null));

  return (
    <div className="stack">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Awaro Gateway</p>
          <h1 className="page-title">{overview.gateway_url || "Gateway"}</h1>
          <div className="hero-meta">
            {sample ? (
              <StatusPill tone={online ? "ok" : "danger"}>
                {online ? "Online" : "Offline"}
              </StatusPill>
            ) : (
              <StatusPill tone="muted">Noch kein Poll</StatusPill>
            )}
            <span>
              Letzter Poll:{" "}
              {formatDateTime(overview.last_poll || sample?.ts || null)}
            </span>
            {sample?.ip ? <span>IP {sample.ip}</span> : null}
            <span>Intervall {overview.poll_interval} s</span>
          </div>
        </div>
        <button
          type="button"
          className="button button-primary"
          onClick={handleRefresh}
          disabled={busy}
        >
          {busy ? "Aktualisiere …" : "Jetzt aktualisieren"}
        </button>
      </section>

      {!overview.poll_enabled ? (
        <div className="alert alert-info">
          Der Hintergrund-Poller ist deaktiviert. Daten werden nur über „Jetzt
          aktualisieren“ geladen.
        </div>
      ) : null}

      <ErrorBanner message={error} />

      {overview.last_error ? (
        <div className="alert alert-error">
          Letzter Fehler: {overview.last_error}
        </div>
      ) : null}

      {!sample ? (
        <div className="alert alert-info">
          Noch keine Messwerte gespeichert. Starte mit „Jetzt aktualisieren“.
        </div>
      ) : null}

      <section className="stat-grid">
        <StatCard
          label="Firmware"
          value={sample?.fw || "—"}
          hint={sample?.hw ? `Hardware ${sample.hw}` : undefined}
        />
        <StatCard label="Uptime" value={formatUptime(sample?.uptime)} />
        <StatCard
          label="Freier Heap"
          value={formatBytes(sample?.heap)}
          hint={sample?.heap ? `${formatNumber(sample.heap)} Byte` : undefined}
        />
        <StatCard
          label="WLAN"
          value={formatRssi(sample?.rssi)}
          hint={sample?.ssid || undefined}
        />
        <StatCard
          label="Sensoren"
          value={formatNumber(overview.counts.sensors)}
          hint={`${overview.counts.integrations} Hooks · ${overview.counts.decoders} Codecs`}
        />
        <StatCard
          label="LNS-Modus"
          value={sample?.mode || "—"}
          hint={
            sample?.ns_ready === null || sample?.ns_ready === undefined
              ? undefined
              : sample.ns_ready
                ? "Netzwerkserver bereit"
                : "Netzwerkserver nicht bereit"
          }
          tone={
            sample?.ns_ready === false
              ? "danger"
              : sample?.ns_ready === true
                ? "ok"
                : undefined
          }
        />
      </section>

      <section className="spark-grid">
        <Sparkline
          label="RSSI"
          values={rssiValues}
          value={formatRssi(sample?.rssi)}
        />
        <Sparkline
          label="Freier Heap"
          values={heapValues}
          value={formatBytes(sample?.heap)}
        />
        <Sparkline
          label="Uptime"
          values={uptimeValues}
          value={formatUptime(sample?.uptime)}
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Ereignisse</h2>
          <Link to="/sensors" className="text-link">
            Sensoren ansehen
          </Link>
        </div>
        {overview.events.length === 0 ? (
          <p className="muted">Noch keine Ereignisse.</p>
        ) : (
          <ul className="event-list">
            {overview.events.map((event) => (
              <li key={event.id} className="event-item">
                <span
                  className={`event-dot tone-${eventTone(event.kind)}`}
                  aria-hidden="true"
                />
                <div className="event-body">
                  <strong>{event.message}</strong>
                  <span>
                    {eventLabel(event.kind)} · {formatDateTime(event.ts)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="muted small">
        LoRaDeck zeigt Gateway- und Sensor-Metadaten. Messwerte werden nicht
        gespeichert – dafür bleibt die native MQTT-Integration von Awaro der
        richtige Weg.
      </p>
    </div>
  );
}
