import styles from "./FindingEditor.module.css";
import type { FindingDraft, FindingEditorState } from "./useFindingEditor.ts";

export function FindingEditor({
  editor,
  runKind,
}: {
  editor: FindingEditorState;
  runKind: "web" | "api";
}) {
  const { draft, setDraft, busy, cancel, save } = editor;
  if (!draft) return null;
  const update = (field: keyof FindingDraft, value: string) =>
    setDraft((previous) => ({ ...previous, [field]: value }));
  const statuses =
    runKind === "web"
      ? [
          ["unvalidated", "unvalidated"],
          ["skipped", "not validated"],
          ["confirmed", "confirmed"],
          ["unconfirmed", "unconfirmed"],
          ["false_positive", "low confidence"],
        ]
      : [
          ["unvalidated", "unvalidated"],
          ["confirmed", "confirmed"],
          ["unconfirmed", "unconfirmed"],
          ["false_positive", "low confidence"],
        ];
  const textFields: Array<[keyof FindingDraft, string]> =
    runKind === "web"
      ? [
          ["description", "Description"],
          ["impact", "Impact"],
          ["likelihood", "Likelihood"],
          ["recommendation", "Recommendation"],
        ]
      : [
          ["description", "Description"],
          ["impact", "Impact"],
          ["recommendation", "Recommendation"],
          ["evidence", "Evidence"],
        ];
  return (
    <div
      className={styles.form}
      onClick={(event) => event.stopPropagation()}
      style={
        runKind === "api"
          ? { borderTop: "1px solid var(--border)", background: "var(--bg)" }
          : undefined
      }
    >
      <div className={styles.fields}>
        <label className={styles.field}>
          <span>Severity</span>
          <select
            value={draft.severity}
            onChange={(event) => update("severity", event.target.value)}
          >
            {["critical", "high", "medium", "low", "info"].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span>Status</span>
          <select
            value={draft.validation_status}
            onChange={(event) => update("validation_status", event.target.value)}
          >
            {statuses.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {runKind === "web" ? (
          <>
            <label className={styles.field} style={{ maxWidth: 90 }}>
              <span>CVSS</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={draft.cvss_score}
                onChange={(event) => update("cvss_score", event.target.value)}
              />
            </label>
            <label className={styles.field} style={{ flex: 2 }}>
              <span>CVSS Vector</span>
              <input
                type="text"
                value={draft.cvss_vector}
                onChange={(event) => update("cvss_vector", event.target.value)}
              />
            </label>
          </>
        ) : (
          <label className={styles.field} style={{ maxWidth: 120 }}>
            <span>OWASP API</span>
            <input
              type="text"
              value={draft.owasp_api_category}
              onChange={(event) => update("owasp_api_category", event.target.value)}
            />
          </label>
        )}
      </div>
      {(
        [
          ["title", "Title"],
          ["affected_url", "Affected URL"],
        ] as const
      ).map(([field, label]) => (
        <label key={field} className={styles.field}>
          <span>{label}</span>
          <input
            type="text"
            value={draft[field]}
            onChange={(event) => update(field, event.target.value)}
          />
        </label>
      ))}
      {textFields.map(([field, label]) => (
        <label key={field} className={styles.field}>
          <span>{label}</span>
          <textarea
            rows={3}
            value={draft[field]}
            onChange={(event) => update(field, event.target.value)}
          />
        </label>
      ))}
      <div className="row" style={{ gap: 8, marginTop: 4, justifyContent: "flex-end" }}>
        <button className="btn ghost sm" disabled={busy} onClick={cancel}>
          Cancel
        </button>
        <button className="btn sm" disabled={busy} onClick={save}>
          {busy ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
