export function ScannerPolicyFields({
  form,
  upd,
  disabled = false
}) {
  return <>
    <div className="form-section-title">Agent</div>
    <label className="toggle-row">
      <input type="checkbox" disabled={disabled} checked={form.execution_monitor_enabled} onChange={e => upd({
        execution_monitor_enabled: e.target.checked
      })} />
      <span>Enable execution monitor</span>
    </label>
    <div className="subtle" style={{ marginBottom: "10px" }}>Detect repeated or stalled agent actions and ask the Mentor to redirect the scan.</div>
    <label className="toggle-row">
      <input type="checkbox" disabled={disabled} checked={form.enforce_full_coverage_obligations} onChange={e => upd({
        enforce_full_coverage_obligations: e.target.checked
      })} />
      <span>Enforce full coverage obligations</span>
    </label>
    <div className="subtle" style={{ marginBottom: "10px" }}>Include strict task-graph completion rules in system prompt before allowing the agent to end the scan.</div>
    <div className="field" style={{ marginTop: "8px" }}>
      <label>Max consecutive text-only turns</label>
      <input type="number" disabled={disabled} min="0" max="50" value={form.max_consecutive_text_turns} onChange={e => upd({
        max_consecutive_text_turns: e.target.value
      })} />
      <div className="field-hint">Maximum turns the model can return text reasoning without making a tool call before terminating (0 = unlimited). Default: 3.</div>
    </div>
  </>;
}
