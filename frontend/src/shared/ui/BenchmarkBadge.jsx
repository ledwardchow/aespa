export function BenchmarkBadge({ href, inline = false }) {
  if (!href) return null;
  if (inline) {
    return (
      <a className="badge neutral" href={href}>
        Evaluated
      </a>
    );
  }
  return (
    <div style={{ marginTop: 5 }}>
      <a className="badge neutral" href={href}>
        Evaluated
      </a>
    </div>
  );
}
