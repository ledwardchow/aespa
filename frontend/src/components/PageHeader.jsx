// The topbar every page repeats: a title (often a breadcrumb) on the left and
// optional action buttons on the right. Crumb is the muted breadcrumb link whose
// inline style was copy-pasted across ~9 pages; Sep is the " / " separator.
export function PageHeader({ title, actions, titleStyle }) {
  return <div className="topbar">
    <div className="topbar-title" style={titleStyle}>{title}</div>
    {actions && <div className="topbar-actions">{actions}</div>}
  </div>;
}

export function Crumb({ href, children }) {
  return <a href={href} style={{ color: "var(--muted)", fontWeight: 400 }}>{children}</a>;
}

export function Sep() {
  return <span className="breadcrumb-sep"> / </span>;
}
