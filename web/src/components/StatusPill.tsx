import type { ReactNode } from "react";
import type { Tone } from "../lib/format";

interface Props {
  tone: Tone;
  children: ReactNode;
}

export default function StatusPill({ tone, children }: Props) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
