import { useEffect, useState } from "react";

import { getScannerPolicy, setOpenAIRefusalRecovery } from "../../shared/api/settings.js";
import { IconCheck } from "../../shared/ui/Icons.jsx";

export function OpenAIRefusalSettings() {
  const [enabled, setEnabled] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getScannerPolicy()
      .then((policy) => setEnabled(policy.openai_refusal_recovery_enabled ?? false))
      .catch((err) => setError(err.message));
  }, []);

  const setRecovery = async (next) => {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const policy = await setOpenAIRefusalRecovery(next);
      setEnabled(policy.openai_refusal_recovery_enabled);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card" style={{ marginTop: 16, maxWidth: 680 }}>
      <div className="form-section-title">OpenAI refusal recovery</div>
      <div className="field-hint" style={{ marginBottom: 12 }}>
        If ChatGPT-plan or Codex refuses a web or API scan step for cybersecurity reasons, AESPA can
        retry that step once with shorter instructions. The first request stays the same. This
        option starts off.
      </div>
      {error && <div className="alert error">{error}</div>}
      {enabled === null && !error && <div className="subtle">Loading…</div>}
      {enabled !== null && (
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={enabled}
            disabled={saving}
            onChange={(event) => setRecovery(event.target.checked)}
          />
          <span>Retry OpenAI cyber refusals with shorter instructions</span>
        </label>
      )}
      {saved && (
        <div className="save-confirm" style={{ marginTop: 8 }}>
          <IconCheck /> Saved
        </div>
      )}
    </div>
  );
}
