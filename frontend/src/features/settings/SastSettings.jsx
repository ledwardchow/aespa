import { PolicySettings } from "./ScannerPolicySettings.jsx";

function BudgetField({ form, upd, field, label, hint }) {
  return (
    <div className="field">
      <label htmlFor={field}>{label}</label>
      <input
        id={field}
        type="number"
        min="1"
        max="1000"
        value={form[field]}
        onChange={(event) => upd({ [field]: event.target.value })}
      />
      {hint && <div className="field-hint">{hint}</div>}
    </div>
  );
}

export function SastPolicyFields({ form, upd }) {
  const adaptive = form.sast_budget_mode === "adaptive";
  return (
    <>
      <section className="policy-group">
        <div className="form-section-title">Discovery budgets</div>
        <div className="policy-section-copy">
          Control how many tool calls each Deep SAST discovery worker can make. Adaptive budgets use
          the worker&apos;s assigned source items, security checks, and files.
        </div>
        <div className="scan-mode-picker">
          <div className="field">
            <label htmlFor="sast-budget-mode">Budget mode</label>
            <select
              id="sast-budget-mode"
              value={form.sast_budget_mode}
              onChange={(event) => upd({ sast_budget_mode: event.target.value })}
            >
              <option value="adaptive">Adaptive</option>
              <option value="fixed">Fixed</option>
            </select>
          </div>
          <div className="scan-mode-summary" aria-live="polite">
            <span className="scan-mode-summary-label">Currently selected</span>
            <strong>{adaptive ? "Adaptive" : "Fixed"}</strong>
            <span>
              {adaptive
                ? "Larger assignments receive more tool calls, within the limits below."
                : "Every discovery worker uses the configured baseline or threat budget."}
            </span>
          </div>
        </div>
        <div className="form-grid two-col">
          <BudgetField
            form={form}
            upd={upd}
            field="sast_baseline_budget"
            label={adaptive ? "Baseline worker minimum" : "Baseline worker budget"}
          />
          <BudgetField
            form={form}
            upd={upd}
            field="sast_threat_budget"
            label={adaptive ? "Threat worker minimum" : "Threat worker budget"}
          />
          {adaptive && (
            <BudgetField
              form={form}
              upd={upd}
              field="sast_worker_budget_max"
              label="Worker maximum"
              hint="The maximum must be at least as large as both worker minimums."
            />
          )}
          <BudgetField form={form} upd={upd} field="sast_closure_budget" label="Closure budget" />
          <BudgetField
            form={form}
            upd={upd}
            field="sast_validator_budget"
            label="Validator budget"
          />
        </div>
      </section>

      <section className="policy-group">
        <div className="form-section-title">Finding policy</div>
        <div className="policy-section-copy">
          Choose which classes of static-analysis findings AESPA can report.
        </div>
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
              checked={form[field]}
              onChange={(event) => upd({ [field]: event.target.checked })}
            />
            <span>{label}</span>
          </label>
        ))}
        <div className="form-grid two-col">
          <div className="field">
            <label htmlFor="sast-min-severity">Minimum severity</label>
            <select
              id="sast-min-severity"
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
            <label htmlFor="sast-min-confidence">Minimum confidence</label>
            <input
              id="sast-min-confidence"
              type="number"
              min="0"
              max="1"
              step="0.05"
              value={form.sast_min_confidence}
              onChange={(event) => upd({ sast_min_confidence: event.target.value })}
            />
          </div>
        </div>
      </section>
    </>
  );
}

export function SastSettings() {
  return <PolicySettings Fields={SastPolicyFields} />;
}
