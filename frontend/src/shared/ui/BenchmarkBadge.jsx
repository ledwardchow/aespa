export function BenchmarkBadge({ href }) {
  if (!href) return null;
  return (
    <div style={{ marginTop: 5 }}>
      <a className="badge neutral" href={href}>
        Evaluated
      </a>
    </div>
  );
}
