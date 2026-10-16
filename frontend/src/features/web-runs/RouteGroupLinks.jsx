import { useEffect, useState } from "react";
import { getDiscoveredTargets } from "../../shared/api/webRuns.js";

function actorLabels(actors) {
  return actors?.length
    ? actors.map((actor) => actor.label || "Unknown account").join(", ")
    : "Unknown";
}

function accessText(observations) {
  return observations?.length
    ? observations
        .map((item) => `${item.label || "Unknown account"}: ${item.method} ${item.result}`)
        .join("; ")
    : "No direct access observed";
}

export function RouteGroupLinks({ runId, routePattern }) {
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [cursors, setCursors] = useState([null]);
  const [page, setPage] = useState(0);
  const [result, setResult] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (input.trim() === search) return undefined;
    const timer = setTimeout(() => {
      setSearch(input.trim());
      setCursors([null]);
      setPage(0);
      setSelectedId(null);
    }, 250);
    return () => clearTimeout(timer);
  }, [input, search]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getDiscoveredTargets(runId, { routePattern, search, cursor: cursors[page] })
      .then((data) => {
        if (!cancelled) {
          setResult(data);
          setSelectedId(null);
        }
      })
      .catch((requestError) => {
        if (!cancelled) setError(requestError.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runId, routePattern, search, cursors, page]);

  const items = result?.items || [];
  const selected = items.find((item) => item.id === selectedId);
  const offset = page * 50;
  const next = () => {
    if (!result?.next_cursor) return;
    setCursors((previous) => [...previous.slice(0, page + 1), result.next_cursor]);
    setPage(page + 1);
  };

  return (
    <div className="route-links" aria-label={`Links for ${routePattern}`}>
      <label className="route-links-search">
        Find a link or account
        <input
          type="search"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="URL or account"
        />
      </label>
      {result?.discovery_completeness && result.discovery_completeness !== "recorded" ? (
        <p className="subtle">
          {result.discovery_completeness === "incomplete"
            ? "Some discovered links could not be saved."
            : "Older crawl data may have missing links."}
        </p>
      ) : null}
      {error ? <div role="alert">Could not load links: {error}</div> : null}
      {loading ? <div className="subtle">Loading links…</div> : null}
      {!loading && !error ? (
        <>
          <div className="route-links-scroll">
            <table className="surface-route-table route-links-table">
              <thead>
                <tr>
                  <th>URL</th>
                  <th>Link seen by</th>
                  <th>Crawled</th>
                  <th>Access observed</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <button
                        type="button"
                        className="route-links-url mono"
                        onClick={() => setSelectedId(selectedId === item.id ? null : item.id)}
                        aria-expanded={selectedId === item.id}
                      >
                        {item.url}
                        {item.state_key ? ` (${item.state_key})` : ""}
                      </button>
                    </td>
                    <td>{actorLabels(item.seen_by)}</td>
                    <td>{item.crawled ? "Yes" : "No"}</td>
                    <td>{accessText(item.access)}</td>
                  </tr>
                ))}
                {!items.length ? (
                  <tr>
                    <td colSpan={4}>No matching links</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
          <div className="route-links-pages">
            <span>
              {items.length ? `${offset + 1}-${offset + items.length}` : 0} of {result?.total ?? 0}{" "}
              links
            </span>
            <div>
              <button
                type="button"
                className="btn sm"
                disabled={page === 0}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </button>{" "}
              <button
                type="button"
                className="btn sm"
                disabled={!result?.next_cursor}
                onClick={next}
              >
                Next
              </button>
            </div>
          </div>
          {selected ? (
            <div className="route-links-detail" aria-label="Link details">
              <strong className="mono">{selected.url}</strong>
              {selected.state_key ? <div>State: {selected.state_key}</div> : null}
              <div>Link seen by: {actorLabels(selected.seen_by)}</div>
              <div>Crawled: {selected.crawled ? "Yes" : "No"}</div>
              <div>Access observed: {accessText(selected.access)}</div>
              <div>
                {selected.selected_checks?.length
                  ? `${selected.selected_checks.length} security checks selected`
                  : "No security check selected"}
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
