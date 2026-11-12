import type { ReactNode } from "react";

interface Props {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "ok" | "warn" | "danger" | "muted";
}

export default function StatCard({ label, value, hint, tone }: Props) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <strong className={tone ? `stat-value tone-${tone}` : "stat-value"}>
        {value}
      </strong>
      {hint ? <span className="stat-hint">{hint}</span> : null}
    </div>
  );
}
