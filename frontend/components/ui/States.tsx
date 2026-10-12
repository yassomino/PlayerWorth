export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="skeleton-stack" role="status" aria-label="Loading data">
      <span className="sr-only">Loading data…</span>
      {Array.from({ length: rows }, (_, i) => (
        <div className="skeleton" key={i} />
      ))}
    </div>
  );
}
export function Unavailable({
  children = "This information isn't available right now.",
}: {
  children?: React.ReactNode;
}) {
  return (
    <div className="unavailable">
      <span aria-hidden="true">—</span>
      <p>{children}</p>
      <p className="small muted">
        You can still explore the rest of PlayerWorth.
      </p>
    </div>
  );
}
