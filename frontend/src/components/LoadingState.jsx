/** Lightweight, consistent loading treatment for run-tab content. */
export function LoadingState({ label = "Loading…", style }) {
  return <div className="subtle run-state" style={style}>{label}</div>;
}
