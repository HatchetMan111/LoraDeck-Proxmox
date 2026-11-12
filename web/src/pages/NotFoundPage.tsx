import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="panel empty-state">
      <h2>Seite nicht gefunden</h2>
      <p className="empty-text">
        Diese Adresse gehört nicht zu LoRaDeck. Vielleicht wurde ein Lesezeichen
        aus einer älteren Version aufgerufen.
      </p>
      <div className="empty-action">
        <Link className="button button-primary" to="/">
          Zur Übersicht
        </Link>
      </div>
    </div>
  );
}
