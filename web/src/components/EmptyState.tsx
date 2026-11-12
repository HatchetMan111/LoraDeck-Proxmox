import type { ReactNode } from "react";

interface Props {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}

export default function EmptyState({ title, children, action }: Props) {
  return (
    <div className="panel empty-state">
      <h2>{title}</h2>
      {children ? <div className="empty-text">{children}</div> : null}
      {action ? <div className="empty-action">{action}</div> : null}
    </div>
  );
}
