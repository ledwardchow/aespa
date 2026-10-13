export function RouteGroupsPanel({ groups = [] }) {
  if (!groups.length) return null;
  return (
    <section
      className="route-groups-panel"
      aria-label="Grouped pages"
      style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)" }}
    >
      <strong>Grouped pages</strong>
      {groups.map((group) => (
        <details key={group.route_pattern} style={{ marginTop: 8 }}>
          <summary>
            {group.label}: {group.route_pattern} - {group.links_seen} links seen,{" "}
            {group.pages_sampled} pages visited
          </summary>
          <div className="subtle">
            The count is links found during this crawl. Testing and findings use the visited example
            URLs.
          </div>
          <ul>
            {(group.example_urls || []).map((url) => (
              <li key={url}>
                <a href={url} target="_blank" rel="noreferrer">
                  {url}
                </a>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </section>
  );
}
