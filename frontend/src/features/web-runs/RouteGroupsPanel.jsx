import { SidePanelSection } from "./SitemapSidePanel.jsx";

function routePath(url) {
  return String(url || "").replace(/^[a-z]+:\/\/[^/]+/i, "") || "/";
}

export function routeGroupTotals(groups = []) {
  return groups.reduce(
    (totals, group) => ({
      links: totals.links + (group.links_seen || 0),
      visited: totals.visited + (group.pages_sampled || 0),
    }),
    { links: 0, visited: 0 },
  );
}

export function routeGroupCountText(groups = []) {
  const totals = routeGroupTotals(groups);
  return (
    `${groups.length} ${groups.length === 1 ? "route" : "routes"} · ` +
    `${totals.links} links found · ${totals.visited} pages visited`
  );
}

function RouteGroupTile({ group, onSelectExample }) {
  const examples = group.example_urls || [];
  return (
    <div className="route-group-tile">
      <span className="route-group-label">{group.label}</span>
      <span className="route-group-path mono" title={group.route_pattern}>
        {routePath(group.route_pattern)}
      </span>
      <span className="route-group-counts">
        {group.links_seen} links found · {group.pages_sampled} visited
        {group.examples_different ? (
          <span className="route-group-different">
            {" "}
            · {group.examples_different} looked different
          </span>
        ) : null}
      </span>
      {examples.length ? (
        <ul className="route-group-examples" aria-label={`Visited ${group.label.toLowerCase()}`}>
          {examples.slice(0, 5).map((url) => (
            <li key={url}>
              <button
                type="button"
                className="route-group-example mono"
                title={url}
                onClick={() => onSelectExample?.(url)}
              >
                {routePath(url)}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function RouteGroupsSummary({ groups = [], onSelectExample }) {
  if (!groups.length) return null;
  const totals = routeGroupTotals(groups);
  return (
    <SidePanelSection
      id="route-groups"
      title="Grouped pages"
      count={`${groups.length} ${groups.length === 1 ? "route" : "routes"} · ${totals.visited} visited`}
    >
      <p className="route-groups-note">
        Only a few pages of each route were visited. Testing uses these pages.
      </p>
      {groups.map((group) => (
        <RouteGroupTile key={group.route_pattern} group={group} onSelectExample={onSelectExample} />
      ))}
    </SidePanelSection>
  );
}

export function RouteGroupsTable({ groups = [] }) {
  return (
    <div className="surface-route-table-wrap">
      <table className="surface-route-table">
        <thead>
          <tr>
            <th>Pages</th>
            <th>Route</th>
            <th>Links found</th>
            <th>Pages visited</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <tr key={group.route_pattern}>
              <td>{group.label}</td>
              <td>
                <span className="mono surface-route-url" title={group.route_pattern}>
                  {routePath(group.route_pattern)}
                </span>
              </td>
              <td>{group.links_seen}</td>
              <td>
                {group.pages_sampled}
                {group.examples_different ? (
                  <span className="subtle surface-route-note">
                    {group.examples_different} looked different
                  </span>
                ) : null}
                {(group.example_urls || []).map((url) => (
                  <span key={url} className="mono subtle surface-route-note" title={url}>
                    {routePath(url)}
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
