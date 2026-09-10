import { useState } from "react";

const STATUS_LABELS = {
  full: "Full",
  partial: "Partial",
  missed: "Missed",
  additional_valid: "Additional valid",
  false_positive: "False positive",
  duplicate: "Duplicate",
  unreviewed: "Unreviewed",
};

function statusFor(item, matches) {
  const match = matches.find(
    (candidate) =>
      candidate.ground_truth_external_id === item.external_id ||
      candidate.ground_truth_id === item.id,
  );
  return { match, status: match?.disposition || "missed" };
}

export function GroundTruthMatrix({ evaluation, onReview }) {
  const [expanded, setExpanded] = useState(null);
  const dataset = evaluation?.ground_truth || evaluation?.dataset || {};
  const items =
    dataset.items || dataset.ground_truth?.items || evaluation?.ground_truth_items || [];
  const matches = evaluation?.matches || [];
  if (!items.length) return <div className="empty-state">No ground-truth items are available.</div>;
  return (
    <div className="benchmark-matrix">
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Expected item</th>
              <th>Category</th>
              <th>Status</th>
              <th>Matched lead</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const { match, status } = statusFor(item, matches);
              const open = expanded === (item.external_id || item.id);
              return (
                <tr key={item.external_id || item.id}>
                  <td>
                    <button
                      className="benchmark-row-toggle"
                      onClick={() => setExpanded(open ? null : item.external_id || item.id)}
                    >
                      {open ? "▾" : "▸"} {item.title || item.external_id || `Item ${item.id}`}
                    </button>
                    {open && (
                      <div className="benchmark-expanded-row">
                        <div>
                          <strong>Root cause:</strong> {item.root_cause || "Not supplied"}
                        </div>
                        <div>
                          <strong>Operation:</strong> {item.affected_operation || "Not supplied"}
                        </div>
                        <div>
                          <strong>Locations:</strong>{" "}
                          {(item.locations || [])
                            .map((location) => `${location.path}:${location.line}`)
                            .join(", ") || "—"}
                        </div>
                        {match?.rationale && (
                          <div>
                            <strong>Rationale:</strong> {match.rationale}
                          </div>
                        )}
                      </div>
                    )}
                  </td>
                  <td>{item.category || "—"}</td>
                  <td>
                    <span className={`benchmark-disposition ${status}`}>
                      {STATUS_LABELS[status] || status}
                    </span>
                  </td>
                  <td>{match?.scan_lead_id ? `Lead #${match.scan_lead_id}` : "—"}</td>
                  <td>
                    {match && (
                      <button className="btn ghost sm" onClick={() => onReview(match)}>
                        Review
                      </button>
                    )}
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
