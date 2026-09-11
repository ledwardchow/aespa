import { useEffect, useState } from "react";

export function MatchReviewPanel({ match, onClose, onSave }) {
  const [disposition, setDisposition] = useState(match?.disposition || "unreviewed");
  const [note, setNote] = useState(match?.review_note || "");
  const [rationale, setRationale] = useState(match?.rationale || "");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setDisposition(match?.disposition || "unreviewed");
    setNote(match?.review_note || "");
    setRationale(match?.rationale || "");
  }, [match]);
  if (!match) return null;
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      await onSave(match.id, { disposition, rationale, review_note: note, human_reviewed: true });
      onClose();
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="benchmark-review-panel">
      <div className="benchmark-panel-heading">
        <strong>Review match</strong>
        <button className="btn ghost sm" onClick={onClose}>
          Close
        </button>
      </div>
      <form onSubmit={submit}>
        <label className="form-label">
          Disposition
          <select
            className="form-input"
            value={disposition}
            onChange={(event) => setDisposition(event.target.value)}
            disabled={busy}
          >
            <option value="full">Full</option>
            <option value="partial">Partial</option>
            <option value="missed">Missed</option>
            <option value="additional_valid">Additional valid</option>
            <option value="false_positive">False positive</option>
            <option value="duplicate">Duplicate</option>
            <option value="unreviewed">Unreviewed</option>
          </select>
        </label>
        <label className="form-label">
          Rationale
          <textarea
            className="form-input"
            value={rationale}
            onChange={(event) => setRationale(event.target.value)}
            rows={3}
            disabled={busy}
          />
        </label>
        <label className="form-label">
          Audit note
          <textarea
            className="form-input"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={2}
            disabled={busy}
          />
        </label>
        <button className="btn primary" type="submit" disabled={busy}>
          {busy ? "Saving…" : "Save review"}
        </button>
      </form>
    </div>
  );
}
