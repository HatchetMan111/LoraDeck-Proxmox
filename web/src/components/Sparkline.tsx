import { useId } from "react";

interface Props {
  values: (number | null)[];
  label: string;
  value?: string;
  height?: number;
}

export default function Sparkline({ values, label, value, height = 48 }: Props) {
  const gradientId = useId().replace(/:/g, "");
  const points = values.filter(
    (item): item is number => item !== null && Number.isFinite(item),
  );

  if (points.length < 2) {
    return (
      <div className="spark-card">
        <div className="spark-head">
          <span>{label}</span>
          <strong>{value ?? "—"}</strong>
        </div>
        <div className="spark-empty">Noch zu wenig Daten</div>
      </div>
    );
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const width = 100;
  const pad = 2;

  const coords = points.map((item, index) => {
    const x = pad + (index * (width - pad * 2)) / (points.length - 1);
    const y = pad + (1 - (item - min) / span) * (height - pad * 2);
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });

  const area = `${pad},${height - pad} ${coords.join(" ")} ${width - pad},${
    height - pad
  }`;

  return (
    <div className="spark-card">
      <div className="spark-head">
        <span>{label}</span>
        <strong>{value ?? "—"}</strong>
      </div>
      <svg
        className="sparkline"
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={label}
      >
        <defs>
          <linearGradient id={`g-${gradientId}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.35" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={area} fill={`url(#g-${gradientId})`} />
        <polyline
          points={coords.join(" ")}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </div>
  );
}
