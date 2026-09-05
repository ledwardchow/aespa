import { useState, useMemo } from "react";

// A compact searchable multi-select list: a filter box above a scrollable list
// of checkboxes. Used to attach existing Sites/API Collections to an
// application, and to preselect application targets in the campaign wizard.
// Kept generic (id/label/checked/onToggle) so both call sites can reuse it
// without a shared giant prop bag.
export function MultiSelectSearch({
  items,
  selectedIds,
  onToggle,
  placeholder = "Search…",
  emptyLabel = "Nothing to select.",
  renderMeta,
}) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => (it.label || "").toLowerCase().includes(q));
  }, [items, query]);

  return (
    <div className="multi-select">
      <input
        type="text"
        className="multi-select-search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
      />
      <div className="multi-select-list">
        {filtered.length === 0 && (
          <div className="subtle" style={{ padding: "10px 4px" }}>
            {emptyLabel}
          </div>
        )}
        {filtered.map((it) => {
          const checked = selectedIds.has(it.id);
          return (
            <label key={it.id} className={"multi-select-row" + (checked ? " checked" : "")}>
              <input type="checkbox" checked={checked} onChange={() => onToggle(it.id)} />
              <span className="multi-select-label">{it.label}</span>
              {renderMeta && <span className="multi-select-meta">{renderMeta(it)}</span>}
            </label>
          );
        })}
      </div>
    </div>
  );
}
