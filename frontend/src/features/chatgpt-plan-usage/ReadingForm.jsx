import * as planUsageApi from "../../shared/api/chatgptPlanUsage.js";
import { useState } from "react";

import { parseDuration } from "./format.js";

const EMPTY = { percent: "", resetsIn: "", resetsAt: "", observedAt: "", note: "" };

export function ReadingForm({ usageWindow, onSaved }) {
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (key, value) => setForm((previous) => ({ ...previous, [key]: value }));

  const save = async (event) => {
    event.preventDefault();
    setError(null);
    const percent = Number(form.percent);
    if (form.percent === "" || !Number.isFinite(percent) || percent < 0 || percent > 100) {
      setError("Enter a usage % between 0 and 100.");
      return;
    }
    const observed = form.observedAt ? new Date(form.observedAt) : new Date();
    let resets = null;
    if (form.resetsIn.trim()) {
      const duration = parseDuration(form.resetsIn);
      if (duration === null) {
        setError('Enter the reset time like "3h 12m" or "2d 4h".');
        return;
      }
      resets = new Date(observed.getTime() + duration);
    } else if (form.resetsAt) {
      resets = new Date(form.resetsAt);
    }
    setBusy(true);
    try {
      await planUsageApi.addPlanUsageReading({
        window: usageWindow,
        used_percent: percent,
        observed_at: form.observedAt ? observed.toISOString() : null,
        resets_at: resets ? resets.toISOString() : null,
        note: form.note,
      });
      setForm(EMPTY);
      onSaved();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="panel" onSubmit={save}>
      <div className="panel-header">
        <h2>Add a reading yourself</h2>
        <span className="subtle">
          {usageWindow === "five_hour" ? "5-hour window" : "Weekly window"} · the reset time lets
          AESPA measure from the start of the window
        </span>
      </div>
      <div className="plan-usage-form">
        <label>
          Used %
          <input
            type="number"
            min="0"
            max="100"
            step="any"
            required
            value={form.percent}
            onChange={(e) => set("percent", e.target.value)}
          />
        </label>
        <label>
          Resets in
          <input
            value={form.resetsIn}
            placeholder={usageWindow === "five_hour" ? "3h 12m" : "4d 6h"}
            onChange={(e) => set("resetsIn", e.target.value)}
          />
        </label>
        <label>
          or resets at
          <input
            type="datetime-local"
            value={form.resetsAt}
            disabled={Boolean(form.resetsIn.trim())}
            onChange={(e) => set("resetsAt", e.target.value)}
          />
        </label>
        <label>
          Reading time
          <input
            type="datetime-local"
            value={form.observedAt}
            onChange={(e) => set("observedAt", e.target.value)}
          />
        </label>
        <label>
          Note
          <input value={form.note} maxLength={500} onChange={(e) => set("note", e.target.value)} />
        </label>
      </div>
      <div className="subtle" style={{ marginTop: 6 }}>
        Leave Reading time empty to use the current time.
      </div>
      {error && <div className="error-text">{error}</div>}
      <div className="form-actions">
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Saving…" : "Add reading"}
        </button>
      </div>
    </form>
  );
}
