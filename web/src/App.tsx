import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Header from "./components/Header";
import LoginForm from "./components/LoginForm";
import { getSession, logout } from "./lib/api";
import BackupsPage from "./pages/BackupsPage";
import DashboardPage from "./pages/DashboardPage";
import FirmwarePage from "./pages/FirmwarePage";
import IntegrationsPage from "./pages/IntegrationsPage";
import NotFoundPage from "./pages/NotFoundPage";
import SensorsPage from "./pages/SensorsPage";
import SettingsPage from "./pages/SettingsPage";
import type { Session } from "./types";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    getSession()
      .then(setSession)
      .catch(() => setSession({ authenticated: false, username: null }));
    const onUnauthorized = () =>
      setSession({ authenticated: false, username: null });
    window.addEventListener("loradeck:unauthorized", onUnauthorized);
    return () =>
      window.removeEventListener("loradeck:unauthorized", onUnauthorized);
  }, []);

  async function handleLogout() {
    try {
      await logout();
    } finally {
      setSession({ authenticated: false, username: null });
    }
  }

  if (!session) {
    return (
      <div className="boot" role="status">
        <span className="spinner" aria-hidden="true" />
        <span>LoRaDeck startet …</span>
      </div>
    );
  }

  if (!session.authenticated) {
    return (
      <div className="login-shell">
        <LoginForm onSuccess={(next) => setSession(next)} />
      </div>
    );
  }

  return (
    <BrowserRouter>
      <div className="app-shell">
        <Header
          username={session.username}
          onLogout={() => {
            void handleLogout();
          }}
        />
        <main className="content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/sensors" element={<SensorsPage />} />
            <Route path="/integrations" element={<IntegrationsPage />} />
            <Route path="/firmware" element={<FirmwarePage />} />
            <Route path="/backups" element={<BackupsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
        <footer className="footer">
          <span>LoRaDeck {new Date().getFullYear()}</span>
          <span>Inoffizieller Begleiter für Awaro-Gateways</span>
        </footer>
      </div>
    </BrowserRouter>
  );
}
