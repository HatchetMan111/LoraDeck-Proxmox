import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import ErrorBanner from "../components/ErrorBanner";
import LoadingPanel from "../components/LoadingPanel";
import StatusPill from "../components/StatusPill";
import {
  errorMessage,
  getSensors,
  refreshGateway,
} from "../lib/api";
import {
  formatDateTime,
  formatNumber,
  statusLabel,
  statusTone,
} from "../lib/format";
import type { Sensor } from "../types";

export default function SensorsPage() {
  const [sensors, setSensors] = useState<Sensor[] | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getSensors()
      .then(setSensors)
      .catch((caught) => setError(errorMessage(caught)));
  }, []);

  const statuses = useMemo(
    () =>
      Array.from(new Set((sensors ?? []).map((sensor) => sensor.status))).sort(),
    [sensors],
  );

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (sensors ?? []).filter((sensor) => {
      const text =
        `${sensor.name} ${sensor.dev_id} ${sensor.decoder} ${sensor.grp}`.toLowerCase();
      const matchesQuery = !needle || text.includes(needle);
      const matchesStatus = status === "all" || sensor.status === status;
      return matchesQuery && matchesStatus;
    });
  }, [sensors, query, status]);

  async function handleRefresh() {
    setBusy(true);
    setError("");
    try {
      await refreshGateway();
      setSensors(await getSensors());
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  if (!sensors) {
    return error ? (
      <div className="stack">
        <ErrorBanner message={error} />
        <Link className="button" to="/settings">
          Einstellungen öffnen
        </Link>
      </div>
    ) : (
      <LoadingPanel />
    );
  }

  return (
    <div className="stack">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">LoRaWAN</p>
          <h1 className="page-title">Sensoren</h1>
          <p className="page-subtitle">
            {sensors.length === 0
              ? "Noch keine Sensoren registriert."
              : `${sensors.length} Sensoren am Gateway registriert.`}
          </p>
        </div>
        <button
          type="button"
          className="button"
          onClick={handleRefresh}
          disabled={busy}
        >
          {busy ? "Aktualisiere …" : "Vom Gateway laden"}
        </button>
      </section>

      <ErrorBanner message={error} />

      {sensors.length === 0 ? (
        <EmptyState
          title="Keine Sensoren gefunden"
          action={
            <Link className="button button-primary" to="/settings">
              Gateway prüfen
            </Link>
          }
        >
          Sobald ein Sensor am Awaro-Gateway joint, erscheint er hier nach dem
          nächsten Poll automatisch.
        </EmptyState>
      ) : (
        <>
          <div className="toolbar">
            <label className="field field-inline">
              <span>Suche</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Name, DevEUI, Decoder …"
              />
            </label>
            <label className="field field-inline">
              <span>Status</span>
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="all">Alle</option>
                {statuses.map((item) => (
                  <option key={item} value={item}>
                    {statusLabel(item)}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="panel table-panel">
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>DevEUI</th>
                    <th>Gruppe</th>
                    <th>Decoder</th>
                    <th>Klasse</th>
                    <th className="num">FCnt</th>
                    <th>Status</th>
                    <th>Letzter Poll</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((sensor) => (
                    <tr key={sensor.dev_id}>
                      <td>
                        <strong>{sensor.name || "—"}</strong>
                      </td>
                      <td className="mono">{sensor.dev_id}</td>
                      <td>{sensor.grp || "—"}</td>
                      <td>{sensor.decoder || "—"}</td>
                      <td>{sensor.cls || "—"}</td>
                      <td className="num">{formatNumber(sensor.fcnt)}</td>
                      <td>
                        <StatusPill tone={statusTone(sensor.status)}>
                          {statusLabel(sensor.status)}
                        </StatusPill>
                      </td>
                      <td title={`Erstmals: ${formatDateTime(sensor.first_seen)}`}>
                        {formatDateTime(sensor.last_seen)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filtered.length === 0 ? (
              <p className="muted table-empty">
                Kein Sensor passt zu Suche und Filter.
              </p>
            ) : null}
          </div>
        </>
      )}

      <p className="muted small">
        FCnt und Status stammen aus der Gateway-API; die Zeitstempel sind
        LoRaDeck-Polls. Messwerte und Payloads zeigt LoRaDeck bewusst nicht an.
      </p>
    </div>
  );
}
