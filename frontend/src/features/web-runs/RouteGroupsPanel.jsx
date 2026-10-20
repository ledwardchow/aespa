import { SidePanelSection } from "./SitemapSidePanel.jsx";
import { Fragment, useState } from "react";
import { RouteGroupLinks } from "./RouteGroupLinks.jsx";

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
    `${totals.links} links found · ${totals.visited} pages crawled`
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
        {group.links_seen} links found · {group.pages_sampled} crawled
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
      count={`${groups.length} ${groups.length === 1 ? "route" : "routes"} · ${totals.visited} crawled`}
    >
      <p className="route-groups-note">
        The crawl sampled pages from each route. Other found links remain available for testing.
      </p>
      {groups.map((group) => (
        <RouteGroupTile key={group.route_pattern} group={group} onSelectExample={onSelectExample} />
      ))}
    </SidePanelSection>
  );
}

export function RouteGroupsTable({ groups = [], runId }) {
  const [expandedRoute, setExpandedRoute] = useState(null);
  return (
    <div className="surface-route-table-wrap">
      <table className="surface-route-table">
        <thead>
          <tr>
            <th>Pages</th>
            <th>Route</th>
            <th>Links found</th>
            <th>Crawled</th>
            <th>Links</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <Fragment key={group.route_pattern}>
              <tr>
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
                </td>
                <td>
                  {runId ? (
                    <button
                      type="button"
                      className="route-links-toggle"
                      aria-expanded={expandedRoute === group.route_pattern}
                      onClick={() =>
                        setExpandedRoute(
                          expandedRoute === group.route_pattern ? null : group.route_pattern,
                        )
                      }
                    >
                      {expandedRoute === group.route_pattern ? "Hide links" : "View links"}
                    </button>
                  ) : null}
                </td>
              </tr>
              {expandedRoute === group.route_pattern ? (
                <tr className="route-links-expanded">
                  <td colSpan={5}>
                    <RouteGroupLinks runId={runId} routePattern={group.route_pattern} />
                  </td>
                </tr>
              ) : null}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
