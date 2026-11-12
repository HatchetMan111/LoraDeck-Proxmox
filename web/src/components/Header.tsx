import { NavLink } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";

const links = [
  { to: "/", label: "Übersicht", end: true },
  { to: "/sensors", label: "Sensoren", end: false },
  { to: "/integrations", label: "Integrationen", end: false },
  { to: "/firmware", label: "Firmware", end: false },
  { to: "/backups", label: "Backups", end: false },
  { to: "/settings", label: "Einstellungen", end: false },
];

interface Props {
  username: string | null;
  onLogout: () => void;
}

export default function Header({ username, onLogout }: Props) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <NavLink to="/" className="brand" end>
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="22" height="22">
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
          <span>LoRaDeck</span>
        </NavLink>
        <nav className="nav" aria-label="Hauptnavigation">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                isActive ? "nav-link is-active" : "nav-link"
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="nav-actions">
          <ThemeToggle />
          {username ? <span className="nav-user">{username}</span> : null}
          <button
            type="button"
            className="button button-ghost button-small"
            onClick={onLogout}
          >
            Abmelden
          </button>
        </div>
      </div>
    </header>
  );
}
