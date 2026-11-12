export default function LoadingPanel({ label = "Wird geladen …" }: { label?: string }) {
  return (
    <div className="panel loading-panel" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
