import { useState, type FormEvent } from "react";
import { errorMessage, login } from "../lib/api";
import type { Session } from "../types";

interface Props {
  onSuccess: (session: Session) => void;
}

export default function LoginForm({ onSuccess }: Props) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const session = await login(username.trim(), password);
      onSuccess(session);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="login-card" onSubmit={handleSubmit}>
      <div className="login-brand">
        <span className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="26" height="26">
            <circle cx="12" cy="15.5" r="1.9" fill="currentColor" />
            <path
              d="M8.6 12.4a4.8 4.8 0 0 1 6.8 0M5.8 9.6a8.8 8.8 0 0 1 12.4 0"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
            />
          </svg>
        </span>
        <div>
          <h1>LoRaDeck</h1>
          <p>Begleiter für dein Awaro-Gateway</p>
        </div>
      </div>

      <label className="field">
        <span>Benutzername</span>
        <input
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          required
        />
      </label>
      <label className="field">
        <span>Passwort</span>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          autoFocus
          required
        />
      </label>

      {error ? (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      ) : null}

      <button type="submit" className="button button-primary" disabled={busy}>
        {busy ? "Anmelden …" : "Anmelden"}
      </button>

      <p className="login-hint">
        Das Initialpasswort wurde bei der Installation einmalig ausgegeben. Bei
        Verlust kann es über den Installer zurückgesetzt werden.
      </p>
    </form>
  );
}
