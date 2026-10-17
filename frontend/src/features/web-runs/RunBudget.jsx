import { useState } from "react";

import * as webRunsApi from "../../shared/api/webRuns.js";
import { fmtUsd } from "../../shared/lib/money.ts";
import styles from "./RunBudget.module.css";

const NEAR_BUDGET_SHARE = 0.8;

export function runSpendUsd(tokenUsage) {
  return Number(tokenUsage?.estimated_total_cost_usd || 0);
}

function unpricedModels(tokenUsage) {
  return Object.entries(tokenUsage?.by_model || {})
    .filter(([, v]) => !v.estimated_cost_available)
    .map(([model]) => model);
}

export function isBudgetReached(run, tokenUsage) {
  return run?.llm_budget_usd != null && runSpendUsd(tokenUsage) >= run.llm_budget_usd;
}

function parseBudget(text) {
  if (text.trim() === "") return null;
  const value = Number(text);
  return Number.isFinite(value) && value > 0 ? value : NaN;
}

export function RunBudgetMeter({ run, tokenUsage, onRunUpdate, onError }) {
  const [draft, setDraft] = useState(null);
  const budget = run?.llm_budget_usd;
  const spend = runSpendUsd(tokenUsage);
  const unpriced = unpricedModels(tokenUsage);

  const save = async () => {
    const value = parseBudget(draft);
    if (Number.isNaN(value)) {
      onError?.("Enter a budget above $0, or leave it empty for no limit.");
      return;
    }
    try {
      onRunUpdate(await webRunsApi.updateRunBudget(run.id, value));
      setDraft(null);
    } catch (e) {
      onError?.(e.message);
    }
  };

  const stop = (e) => e.stopPropagation();

  if (draft !== null) {
    return (
      <span className={styles.meter} onClick={stop}>
        <span className="token-bar-sep">·</span>
        <span className={styles.label}>Budget</span>
        <span className={styles.amount}>$</span>
        <input
          className={styles.input}
          type="number"
          min="0.01"
          step="0.01"
          placeholder="No limit"
          autoFocus
          onFocus={(e) => e.target.select()}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") save();
            if (e.key === "Escape") setDraft(null);
          }}
        />
        <button type="button" className={styles.link} onClick={save}>
          Save
        </button>
        <button type="button" className={styles.link} onClick={() => setDraft(null)}>
          Cancel
        </button>
      </span>
    );
  }

  if (budget == null) {
    return (
      <span className={styles.meter} onClick={stop}>
        <span className="token-bar-sep">·</span>
        <span className={styles.label}>Budget</span>
        <button type="button" className={styles.link} onClick={() => setDraft("")}>
          Set budget
        </button>
      </span>
    );
  }

  const share = Math.min(1, spend / budget);
  const state = spend >= budget ? styles.reached : share >= NEAR_BUDGET_SHARE ? styles.near : "";
  return (
    <span className={`${styles.meter} ${state}`} onClick={stop}>
      <span className="token-bar-sep">·</span>
      <span className={styles.label}>Budget</span>
      <span className={styles.track}>
        <span className={styles.fill} style={{ width: `${Math.round(share * 100)}%` }} />
      </span>
      <span className={styles.amount}>
        {fmtUsd(spend)} of {fmtUsd(budget)}
      </span>
      <button type="button" className={styles.link} onClick={() => setDraft(String(budget))}>
        Edit
      </button>
      {unpriced.length > 0 ? (
        <span
          className={styles.unpriced}
          title={`No price is set for ${unpriced.join(", ")}, so its spend counts as $0 toward the budget.`}
        >
          {unpriced.length === 1 ? "1 model has" : `${unpriced.length} models have`} no price
        </span>
      ) : null}
    </span>
  );
}

export function BudgetPausedBanner({ run, tokenUsage, onRunUpdate, onResume }) {
  const [draft, setDraft] = useState(() => String(Math.ceil((run.llm_budget_usd || 0) * 2)));
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const spend = runSpendUsd(tokenUsage);

  const apply = async (value) => {
    if (value !== null && !(value > spend)) {
      setError(`Set a budget above ${fmtUsd(spend)} to resume.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      onRunUpdate(await webRunsApi.updateRunBudget(run.id, value));
      await onResume();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const saveAndResume = () => {
    const value = parseBudget(draft);
    if (value === null || Number.isNaN(value)) {
      setError("Enter a budget above $0.");
      return;
    }
    apply(value);
  };

  return (
    <div className={styles.banner} role="status">
      <div className={styles.bannerText}>
        <div className={styles.bannerTitle}>Budget reached ({fmtUsd(run.llm_budget_usd)})</div>
        All LLM work on this run is paused, including A.L.I.C.E. Raise the budget to resume.
      </div>
      <label className={styles.bannerField}>
        New budget $
        <input
          className={styles.input}
          type="number"
          min="0.01"
          step="0.01"
          onFocus={(e) => e.target.select()}
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setError(null);
          }}
        />
      </label>
      <button type="button" className="btn sm" disabled={busy} onClick={saveAndResume}>
        Save and resume
      </button>
      <button
        type="button"
        className="btn secondary sm"
        disabled={busy}
        onClick={() => apply(null)}
      >
        Remove limit
      </button>
      {error ? <div className={styles.error}>{error}</div> : null}
    </div>
  );
}
