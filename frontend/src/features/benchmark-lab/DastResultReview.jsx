import { useMemo, useState } from "react";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import styles from "./DastResultReview.module.css";

const rank = { missing: 0, partial: 1, full: 2 };
const severityRank = { critical: 0, high: 1, medium: 2, low: 3, informational: 4 };

export function DastResultReview({ result, onSaved }) {
  const [selectedId, setSelectedId] = useState(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [groupBy, setGroupBy] = useState("none");
  const [edit, setEdit] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const rows = useMemo(() => {
    const byId = new Map(result.rows.map((row) => [row.external_id, row]));
    return (result.ground_truth.items || [])
      .map((item) => ({ item, row: byId.get(item.external_id) }))
      .filter(
        ({ item, row }) =>
          `${item.external_id} ${item.title || ""} ${item.description || ""}`
            .toLowerCase()
            .includes(query.trim().toLowerCase()) &&
          (status === "all" || (row?.disposition || "missing") === status),
      )
      .sort((a, b) => {
        if (groupBy !== "none") {
          const left = String(a.item[groupBy] || "");
          const right = String(b.item[groupBy] || "");
          const groupOrder =
            groupBy === "severity"
              ? (severityRank[left.toLowerCase()] ?? 5) -
                  (severityRank[right.toLowerCase()] ?? 5) || left.localeCompare(right)
              : left.localeCompare(right);
          if (groupOrder) return groupOrder;
        }
        return rank[a.row?.disposition || "missing"] - rank[b.row?.disposition || "missing"];
      });
  }, [result, query, status, groupBy]);
  const selected = rows.find(({ item }) => item.external_id === selectedId) || rows[0];
  const groups =
    groupBy === "none"
      ? [{ label: null, rows }]
      : [...Map.groupBy(rows, ({ item }) => item[groupBy] || "Unspecified")].map(
          ([label, groupRows]) => ({ label, rows: groupRows }),
        );
  const findings = new Map((result.findings || []).map((finding) => [finding.id, finding]));
  const save = async () => {
    if (!edit || busy) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await benchmarkApi.reviewBenchmarkResult(result.id, edit.external_id, {
        disposition: edit.disposition,
        finding_ids: edit.disposition === "missing" ? [] : edit.finding_ids,
        note: edit.note,
      });
      onSaved(updated);
      setEdit(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className={styles.review}>
      <div className={styles.filters}>
        <label>
          Search findings
          <input
            className="input"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setEdit(null);
            }}
            placeholder="ID, title, or description"
          />
        </label>
        <label>
          Result
          <select
            className="select"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setEdit(null);
            }}
          >
            <option value="all">All results</option>
            <option value="missing">Missing</option>
            <option value="partial">Partial</option>
            <option value="full">Full</option>
          </select>
        </label>
        <label>
          Group by
          <select
            className="select"
            value={groupBy}
            onChange={(event) => {
              setGroupBy(event.target.value);
              setEdit(null);
            }}
          >
            <option value="none">Result</option>
            <option value="category">OWASP category</option>
            <option value="severity">Severity</option>
          </select>
        </label>
      </div>
      <div className={styles.columns}>
        <div className={styles.list} aria-label="Ground truth findings">
          {rows.length ? (
            groups.map((group) => (
              <div key={group.label || "all"}>
                {group.label && (
                  <h4 className={styles.groupHeading}>
                    {group.label} ({group.rows.length})
                  </h4>
                )}
                {group.rows.map(({ item, row }) => (
                  <button
                    key={item.external_id}
                    type="button"
                    className={`${styles.row} ${selected?.item.external_id === item.external_id ? styles.active : ""}`}
                    onClick={() => {
                      setSelectedId(item.external_id);
                      setEdit(null);
                    }}
                    aria-current={
                      selected?.item.external_id === item.external_id ? "true" : undefined
                    }
                  >
                    <span className={styles.rowTop}>
                      <span>{item.external_id}</span>
                      <span className={`benchmark-disposition ${row?.disposition || "missing"}`}>
                        {row?.disposition || "missing"}
                      </span>
                    </span>
                    <strong>{item.title || item.description || "Untitled finding"}</strong>
                  </button>
                ))}
              </div>
            ))
          ) : (
            <p className="subtle">No findings match these filters.</p>
          )}
        </div>
        <section className={styles.detail} aria-label="Finding review">
          {selected && (
            <>
              <div className={styles.detailHeading}>
                <span className="subtle">{selected.item.external_id}</span>
                <span className={`benchmark-disposition ${selected.row?.disposition || "missing"}`}>
                  {selected.row?.disposition || "missing"}
                  {selected.row?.reviewed ? " (reviewed)" : ""}
                </span>
              </div>
              <h3>{selected.item.title || "Untitled finding"}</h3>
              <p>
                {selected.item.description ||
                  selected.item.root_cause ||
                  "No description supplied."}
              </p>
              <h4>Comparison reason</h4>
              <p>{selected.row?.reason || "No reason recorded."}</p>
              <h4>Matching scan findings</h4>
              <p>
                {selected.row?.finding_ids?.length
                  ? selected.row.finding_ids
                      .map((id) => findings.get(id)?.reference || `#${id}`)
                      .join(", ")
                  : "No matching findings."}
              </p>
              {error && (
                <div className="alert error" role="alert">
                  {error}
                </div>
              )}
              {edit?.external_id === selected.item.external_id ? (
                <div className="benchmark-review-form">
                  <label>
                    Result
                    <select
                      className="select"
                      value={edit.disposition}
                      onChange={(event) => setEdit({ ...edit, disposition: event.target.value })}
                    >
                      <option value="full">Full</option>
                      <option value="partial">Partial</option>
                      <option value="missing">Missing</option>
                    </select>
                  </label>
                  {edit.disposition !== "missing" && (
                    <fieldset>
                      <legend>Matching findings</legend>
                      {(result.findings || []).map((finding) => (
                        <label key={finding.id}>
                          <input
                            type="checkbox"
                            checked={edit.finding_ids.includes(finding.id)}
                            onChange={(event) =>
                              setEdit({
                                ...edit,
                                finding_ids: event.target.checked
                                  ? [...edit.finding_ids, finding.id]
                                  : edit.finding_ids.filter((id) => id !== finding.id),
                              })
                            }
                          />{" "}
                          {finding.reference} - {finding.title}
                        </label>
                      ))}
                    </fieldset>
                  )}
                  <label>
                    Reason
                    <textarea
                      value={edit.note}
                      onChange={(event) => setEdit({ ...edit, note: event.target.value })}
                    />
                  </label>
                  <div className={styles.actions}>
                    <button className="btn primary sm" type="button" disabled={busy} onClick={save}>
                      Save review
                    </button>
                    <button className="btn ghost sm" type="button" onClick={() => setEdit(null)}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  className="btn secondary sm"
                  type="button"
                  onClick={() =>
                    setEdit({
                      external_id: selected.item.external_id,
                      disposition: selected.row?.disposition || "missing",
                      finding_ids: selected.row?.finding_ids || [],
                      note: selected.row?.review_note || "",
                    })
                  }
                >
                  Review result
                </button>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
