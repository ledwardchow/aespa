// The topbar every page repeats: a title (often a breadcrumb) on the left and
// optional action buttons on the right. Crumb is the muted breadcrumb link whose
// inline style was copy-pasted across ~9 pages; Sep is the " / " separator.
export function PageHeader({ title, actions, titleStyle, className = "" }) {
  return (
    <div className={"topbar" + (className ? ` ${className}` : "")}>
      <div className="topbar-layout">
        <div className="topbar-title" style={titleStyle}>
          {title}
        </div>
        {actions && <div className="topbar-actions">{actions}</div>}
      </div>
    </div>
  );
}

export function Crumb({ href, children }) {
  return (
    <a href={href} style={{ color: "var(--muted)", fontWeight: 400 }}>
      {children}
    </a>
  );
}

export function Sep() {
  return <span className="breadcrumb-sep"> / </span>;
}

// Section / parent / current page. Each item is { label, href } and the last one
// (the current page) is plain text. Spacing comes from CSS so it survives flex
// containers, which drop the plain-text spaces Sep relies on.
export function Breadcrumbs({ items }) {
  const shown = items.filter(Boolean);
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      {shown.map((item, index) => (
        <span className="breadcrumbs-item" key={`${index}-${item.href || ""}`}>
          {index > 0 && (
            <span className="breadcrumb-sep" aria-hidden="true">
              /
            </span>
          )}
          {item.href && index < shown.length - 1 ? (
            <Crumb href={item.href}>{item.label}</Crumb>
          ) : (
            <span className="breadcrumbs-current">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
