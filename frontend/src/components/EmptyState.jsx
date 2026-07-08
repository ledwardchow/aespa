// Standard empty-state card: icon + message + optional sub-text + optional action.
// title/sub accept any node so callers can pass rich JSX (bold, <br/>, links).
export function EmptyState({ icon = "⬡", title, sub, action, style }) {
  return <div className="empty-state" style={style}>
    {icon && <div className="empty-icon">{icon}</div>}
    <div className="empty-msg">{title}</div>
    {sub && <div className="empty-sub">{sub}</div>}
    {action}
  </div>;
}
