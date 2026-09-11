export function ScannerPolicyFields({ form, upd, disabled = false }) {
  return (
    <>
      <div className="form-section-title">Agent</div>
      <label className="toggle-row">
        <input
          type="checkbox"
          disabled={disabled}
          checked={form.disable_deterministic_checks}
          onChange={(e) =>
            upd({
              disable_deterministic_checks: e.target.checked,
            })
          }
        />
        <span>Disable all deterministic checks</span>
      </label>
      <div className="subtle" style={{ marginBottom: "10px" }}>
        Skip automatic JavaScript sink, TLS, authentication, IDOR, and probe-result checks. The Test
        Lead will continue with LLM-driven testing.
      </div>
      <label className="toggle-row">
        <input
          type="checkbox"
          disabled={disabled}
          checked={form.execution_monitor_enabled}
          onChange={(e) =>
            upd({
              execution_monitor_enabled: e.target.checked,
            })
          }
        />
        <span>Enable execution monitor</span>
      </label>
      <div className="subtle" style={{ marginBottom: "10px" }}>
        Detect repeated or stalled agent actions and ask the Mentor to redirect the scan.
      </div>
      <label className="toggle-row">
        <input
          type="checkbox"
          disabled={disabled}
          checked={form.enforce_full_coverage_obligations}
          onChange={(e) =>
            upd({
              enforce_full_coverage_obligations: e.target.checked,
            })
          }
        />
        <span>Enforce full coverage obligations</span>
      </label>
      <div className="subtle" style={{ marginBottom: "10px" }}>
        Include strict task-graph completion rules in system prompt before allowing the agent to end
        the scan.
      </div>
      <div className="field" style={{ marginTop: "8px" }}>
        <label>Standard mode coverage target (%)</label>
        <input
          type="number"
          disabled={disabled}
          min="1"
          max="100"
          value={form.standard_coverage_percent}
          onChange={(e) =>
            upd({
              standard_coverage_percent: e.target.value,
            })
          }
        />
        <div className="field-hint">
          Standard mode will not accept completion until the Test Lead has exercised this percentage
          of applicable coverage cells. Default: 60%.
        </div>
      </div>
      <div className="form-section-title">Static analysis</div>
      {[
        ["sast_rate_limit_findings", "Rate limiting and brute-force resistance"],
        ["sast_race_condition_findings", "Race conditions and concurrency invariants"],
        ["sast_audit_logging_findings", "Audit logging and detection gaps"],
        ["sast_defense_in_depth_findings", "Defense-in-depth weaknesses"],
        ["sast_dependency_findings", "Vulnerable dependencies"],
      ].map(([field, label]) => (
        <label className="toggle-row" key={field}>
          <input
            type="checkbox"
            disabled={disabled}
            checked={form[field]}
            onChange={(event) => upd({ [field]: event.target.checked })}
          />
          <span>{label}</span>
        </label>
      ))}
      <div className="form-grid two-col">
        <div className="field">
          <label>Minimum severity</label>
          <select
            disabled={disabled}
            value={form.sast_min_severity}
            onChange={(event) => upd({ sast_min_severity: event.target.value })}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
        <div className="field">
          <label>Minimum confidence</label>
          <input
            type="number"
            disabled={disabled}
            min="0"
            max="1"
            step="0.05"
            value={form.sast_min_confidence}
            onChange={(event) => upd({ sast_min_confidence: event.target.value })}
          />
        </div>
      </div>
      <div className="form-grid two-col">
        {[
          ["sast_baseline_budget", "Baseline tool-call budget"],
          ["sast_threat_budget", "Threat worker budget"],
          ["sast_closure_budget", "Closure budget"],
          ["sast_validator_budget", "Validator budget"],
        ].map(([field, label]) => (
          <div className="field" key={field}>
            <label>{label}</label>
            <input
              type="number"
              disabled={disabled}
              min="1"
              max="1000"
              value={form[field]}
              onChange={(event) => upd({ [field]: event.target.value })}
            />
          </div>
        ))}
      </div>
      <label className="toggle-row">
        <input
          type="checkbox"
          disabled={disabled}
          checked={form.strict_locator_enforcement}
          onChange={(e) =>
            upd({
              strict_locator_enforcement: e.target.checked,
            })
          }
        />
        <span>Strict locator enforcement</span>
      </label>
      <div className="subtle" style={{ marginBottom: "10px" }}>
        Treat browser fill/click steps with no resolvable selector, testid, or role+name as a hard
        failure instead of silently skipping, so the agent retries and repeated failures trip the
        URL circuit breaker.
      </div>
      <div className="field" style={{ marginTop: "8px" }}>
        <label>Max consecutive text-only turns</label>
        <input
          type="number"
          disabled={disabled}
          min="0"
          max="50"
          value={form.max_consecutive_text_turns}
          onChange={(e) =>
            upd({
              max_consecutive_text_turns: e.target.value,
            })
          }
        />
        <div className="field-hint">
          Maximum turns the model can return text reasoning without making a tool call before
          terminating (0 = unlimited). Default: unlimited.
        </div>
      </div>
    </>
  );
}
