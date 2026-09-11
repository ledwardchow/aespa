import * as apiCollectionsApi from "../../shared/api/apiCollections.js";
import { useState, useEffect } from "react";

export function ApiRunEndpointsTab({ run }) {
  const [endpoints, setEndpoints] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!run) return;
    apiCollectionsApi
      .listApiEndpoints(run.collection_id)
      .then((data) => {
        setEndpoints(data || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [run]);
  if (loading)
    return (
      <div
        className="subtle"
        style={{
          padding: 24,
        }}
      >
        Loading endpoints…
      </div>
    );
  if (!endpoints.length)
    return (
      <div
        className="subtle"
        style={{
          padding: 24,
          textAlign: "center",
        }}
      >
        No endpoints found. Upload and parse API documentation first.
      </div>
    );
  const parsedNotes = (ep) => {
    try {
      return JSON.parse(ep.prereq_notes || "[]");
    } catch {
      return [];
    }
  };
  const readinessIcon = (ok) =>
    ok ? (
      <span
        style={{
          color: "var(--success,#4caf50)",
        }}
      >
        ✔
      </span>
    ) : (
      <span
        style={{
          color: "var(--danger,#f44336)",
        }}
      >
        ✘
      </span>
    );
  return (
    <div
      className="run-endpoints-tab"
      style={{
        padding: "16px",
      }}
    >
      <h3
        style={{
          marginBottom: 12,
        }}
      >
        Endpoint Prerequisites
      </h3>
      <div className="run-endpoints-table-wrap">
        <table
          className="data-table"
          style={{
            width: "100%",
            borderCollapse: "collapse",
          }}
        >
          <thead>
            <tr>
              <th>Method</th>
              <th>Path</th>
              <th>Auth Req.</th>
              <th title="Enough info to probe this endpoint">Testable?</th>
              <th title="Have credentials for auth-required paths">Auth Testable?</th>
              <th>Notes / Gaps</th>
            </tr>
          </thead>
          <tbody>
            {endpoints.map((ep) => {
              const notes = parsedNotes(ep);
              return (
                <tr key={ep.id}>
                  <td>
                    <span className={"method-badge method-" + ep.method.toLowerCase()}>
                      {ep.method}
                    </span>
                  </td>
                  <td
                    className="mono"
                    style={{
                      fontSize: 12,
                    }}
                  >
                    {ep.path}
                  </td>
                  <td
                    style={{
                      textAlign: "center",
                    }}
                  >
                    {ep.auth_required ? (
                      <span className="badge warning">Auth</span>
                    ) : (
                      <span className="badge neutral">Open</span>
                    )}
                  </td>
                  <td
                    style={{
                      textAlign: "center",
                    }}
                  >
                    {readinessIcon(ep.prereq_can_test)}
                  </td>
                  <td
                    style={{
                      textAlign: "center",
                    }}
                  >
                    {readinessIcon(ep.prereq_can_test_auth)}
                  </td>
                  <td
                    style={{
                      fontSize: 11,
                      color: notes.length ? "var(--danger,#f44336)" : "var(--muted)",
                    }}
                  >
                    {notes.length ? notes.join(" · ") : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── ApiRunWorkProgramTab — coverage matrix + live updates ─────────────────────
