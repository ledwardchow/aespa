import { useState } from "react";
import styles from "./BenchmarkSettings.module.css";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";

function DatasetRow({ dataset, targets, onChange }) {
  const assignments = dataset.assignments || [];
  const [target, setTarget] = useState(
    assignments.length === 1 ? `${assignments[0].target_kind}:${assignments[0].target_id}` : "",
  );
  const [label, setLabel] = useState(dataset.label || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const choices = [
    ...targets.sites.map((item) => ({ ...item, kind: "site", type: "App" })),
    ...targets.apis.map((item) => ({ ...item, kind: "api", type: "API" })),
  ];
  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const [kind, id] = target.split(":");
      await benchmarkApi.updateBenchmarkDatasetDetails(dataset.id, {
        label,
        target_kind: kind || null,
        target_id: id ? Number(id) : null,
      });
      await onChange();
      setMessage("Saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await benchmarkApi.deleteBenchmarkDataset(dataset.id);
      await onChange();
    } catch (err) {
      setError(err.message);
      setConfirmDelete(false);
    } finally {
      setBusy(false);
    }
  }
  const assignedNames = assignments.map(
    (assignment) =>
      choices.find(
        (item) => item.kind === assignment.target_kind && item.id === assignment.target_id,
      )?.name || "Removed target",
  );
  const selected = choices.find((item) => `${item.kind}:${item.id}` === target);
  const replacing = selected?.dataset && selected.dataset.id !== dataset.id;
  return (
    <section className={`card ${styles.dataset}`} aria-label={dataset.name}>
      <div className={styles.datasetHeader}>
        <h3>{dataset.name}</h3>
        <span className={styles.itemCount}>{dataset.item_count} items</span>
      </div>
      <form onSubmit={save}>
        <fieldset className={styles.fields} disabled={busy}>
          <div className={styles.fieldGrid}>
            <label className="field">
              App or API
              <select
                className="select"
                value={target}
                onChange={(event) => setTarget(event.target.value)}
              >
                <option value="">No app or API</option>
                {choices.map((item) => (
                  <option key={`${item.kind}:${item.id}`} value={`${item.kind}:${item.id}`}>
                    {item.type}: {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Custom label
              <input
                type="text"
                value={label}
                maxLength={200}
                placeholder="Optional label"
                onChange={(event) => setLabel(event.target.value)}
              />
            </label>
          </div>
          {assignments.length > 1 && (
            <p>
              Currently assigned to {assignedNames.join(", ")}. Saving will replace these
              assignments with your selection.
            </p>
          )}
          {replacing && (
            <p>This will replace {selected.name}&apos;s current ground truth dataset.</p>
          )}
          <div className={`form-actions ${styles.actions}`}>
            <button className="btn primary" type="submit">
              {busy ? "Working..." : "Save"}
            </button>
            <button
              className={`btn ghost ${styles.deleteButton}`}
              type="button"
              onClick={() => setConfirmDelete(true)}
            >
              Delete
            </button>
          </div>
          {confirmDelete && (
            <div className={styles.confirmation} role="group" aria-label="Confirm deletion">
              <p>
                Delete {dataset.name}? This removes the dataset and its app/API assignments. Saved
                benchmarks must be deleted first.
              </p>
              <button className="btn danger" type="button" onClick={remove}>
                Delete dataset
              </button>{" "}
              <button
                className="btn secondary"
                type="button"
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </button>
            </div>
          )}
        </fieldset>
      </form>
      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}

export function GroundTruthDatasets({ datasets, targets, onChange }) {
  return (
    <section className={styles.datasets}>
      <div>
        <h2 className="form-section-title">Ground truth datasets</h2>
        <p className="policy-section-copy">
          Assign each file to an app or API and add an optional label. Each target uses one dataset.
        </p>
      </div>
      {datasets.length === 0 && (
        <p>No saved datasets. Upload ground truth when creating a benchmark.</p>
      )}
      {datasets.map((dataset) => (
        <DatasetRow
          key={`${dataset.id}:${dataset.updated_at || ""}`}
          dataset={dataset}
          targets={targets}
          onChange={onChange}
        />
      ))}
    </section>
  );
}
