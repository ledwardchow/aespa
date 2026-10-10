import { useState } from "react";

import { saveBenchmarkResultComment } from "../../shared/api/benchmarkLab.js";

export function BenchmarkResultComment({ result, onSaved }) {
  const [draft, setDraft] = useState(result.comment || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const updated = await saveBenchmarkResultComment(result.id, draft);
      setDraft(updated.comment || "");
      onSaved(updated);
    } catch (cause) {
      setError(cause.message || "Comment could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="benchmark-result-comment">
      <h3>Comment</h3>
      <textarea
        aria-label="Comment"
        value={draft}
        maxLength={2000}
        rows={3}
        onChange={(event) => setDraft(event.target.value)}
      />
      <button
        className="btn secondary sm"
        type="button"
        onClick={save}
        disabled={saving || draft.trim() === (result.comment || "")}
      >
        {saving ? "Saving…" : "Save comment"}
      </button>
      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
