import { useEffect, useState } from "react";
import EmptyState from "../components/EmptyState";
import ErrorBanner from "../components/ErrorBanner";
import LoadingPanel from "../components/LoadingPanel";
import {
  backupDownloadUrl,
  createBackup,
  deleteBackup,
  errorMessage,
  listBackups,
} from "../lib/api";
import { formatBytes, formatDateTime } from "../lib/format";
import type { Backup } from "../types";

export default function BackupsPage() {
  const [backups, setBackups] = useState<Backup[] | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listBackups()
      .then(setBackups)
      .catch((caught) => setError(errorMessage(caught)));
  }, []);

  async function handleCreate() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const item = await createBackup();
      setBackups(await listBackups());
      setNotice(`Backup ${item.filename} erstellt.`);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Backup wirklich löschen?")) {
      return;
    }
    setError("");
    setNotice("");
    try {
      await deleteBackup(id);
      setBackups(await listBackups());
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  if (!backups) {
    return error ? <ErrorBanner message={error} /> : <LoadingPanel />;
  }

  return (
    <div className="stack">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Sicherung</p>
          <h1 className="page-title">Backups</h1>
          <p className="page-subtitle">
            Gateway-Konfiguration ohne Secrets plus LoRaWAN-Export.
          </p>
        </div>
        <button
          type="button"
          className="button button-primary"
          onClick={handleCreate}
          disabled={busy}
        >
          {busy ? "Erstelle …" : "Backup erstellen"}
        </button>
      </section>

      {notice ? <div className="alert alert-success">{notice}</div> : null}
      <ErrorBanner message={error} />

      {backups.length === 0 ? (
        <EmptyState title="Noch kein Backup">
          Erstelle eine Sicherung, bevor du Firmware aktualisierst oder die
          Gateway-Konfiguration änderst.
        </EmptyState>
      ) : (
        <div className="panel table-panel">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Zeitpunkt</th>
                  <th>Art</th>
                  <th className="num">Größe</th>
                  <th>SHA-256</th>
                  <th className="actions">Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {backups.map((item) => (
                  <tr key={item.id}>
                    <td>{formatDateTime(item.ts)}</td>
                    <td>{item.kind}</td>
                    <td className="num">{formatBytes(item.size)}</td>
                    <td className="mono" title={item.sha256}>
                      {item.sha256.slice(0, 12)}…
                    </td>
                    <td className="actions">
                      <a
                        className="button button-small"
                        href={backupDownloadUrl(item.id)}
                      >
                        Download
                      </a>
                      <button
                        type="button"
                        className="button button-small button-danger"
                        onClick={() => handleDelete(item.id)}
                      >
                        Löschen
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="alert alert-warning">
        Backups enthalten die LoRaWAN-Schlüssel deiner Sensoren. Bewahre sie
        sicher auf – Ablage unter <code>/var/lib/loradeck/backups</code>.
      </div>
    </div>
  );
}
