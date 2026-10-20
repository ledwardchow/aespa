import * as planUsageApi from "../../shared/api/chatgptPlanUsage.js";
import { useCallback, useEffect, useState } from "react";

import { fmtTok } from "../../shared/ui/TokenUsageBar.jsx";
import { usePagedRows } from "./Pager.jsx";
import { UsageChart } from "./UsageChart.jsx";
import { fmtPercent, fmtTime, fmtUsd } from "./format.js";
import "./chatgpt-plan-usage.css";

const WINDOWS = [
  { id: "weekly", label: "Weekly window" },
  { id: "five_hour", label: "5-hour window" },
];

function StatCard({ label, value, detail }) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

const SETTINGS_HREF = `#/extensions/${planUsageApi.PLAN_USAGE_EXTENSION_ID}/settings`;

function CodexStatus({ status, usageWindow, busy, onCheck }) {
  const windowLabel = usageWindow === "five_hour" ? "5-hour" : "weekly";
  const reported = status?.windows?.find((item) => item.window === usageWindow);
  let message;
  if (!status) {
    message = "Codex has not been checked yet.";
  } else if (!status.ok) {
    message = `Could not read usage from Codex: ${status.error}`;
  } else if (reported) {
    message = `Codex reports ${fmtPercent(reported.used_percent)} of the ${windowLabel} limit used${
      reported.resets_at ? `, resetting ${fmtTime(reported.resets_at)}` : ""
    }.`;
  } else {
    message = `Codex did not report a ${windowLabel} limit for this plan.`;
  }
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Codex</h2>
        <span className="subtle">
          {status?.email
            ? `${status.email}${status.plan_type ? ` · ${status.plan_type}` : ""} · `
            : ""}
          {status?.checked_at ? `checked ${fmtTime(status.checked_at)}` : "not checked"}
        </span>
        <span className="plan-usage-header-actions">
          <a className="btn ghost sm" href={SETTINGS_HREF}>
            Settings
          </a>
          <button className="btn secondary sm" type="button" disabled={busy} onClick={onCheck}>
            {busy ? "Checking…" : "Check now"}
          </button>
        </span>
      </div>
      <div className={status && !status.ok ? "error-text" : ""}>{message}</div>
      {status?.same_account === false ? (
        <div className="alert warning" style={{ marginTop: 10 }}>
          Codex is signed in as {status.email}, but the ChatGPT plan provider uses{" "}
          {status.chatgpt_plan_email}. Only Codex CLI usage is counted until they match.
        </div>
      ) : null}
    </div>
  );
}

function Summary({ data }) {
  const estimate = data.estimate;
  const current = data.timeline.current;
  const perPercent = estimate?.tokens_per_percent;
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Estimate</h2>
        <span className="subtle">
          {estimate
            ? `Based on ${fmtPercent(estimate.percent_measured)} of usage across ${estimate.segments} interval${estimate.segments === 1 ? "" : "s"}`
            : "Appears once AESPA has used the plan between two readings in the same window"}
        </span>
      </div>
      <div className="stats-grid">
        <StatCard
          label="100% at API prices"
          value={fmtUsd(estimate?.usd_for_full_window)}
          detail={
            estimate?.usd_per_percent != null ? `${fmtUsd(estimate.usd_per_percent)} per 1%` : null
          }
        />
        <StatCard
          label="Estimated usage now"
          value={fmtPercent(current?.estimated_percent_now)}
          detail={
            current ? `Last reading ${fmtPercent(current.used_percent)}` : "No reading this window"
          }
        />
        <StatCard
          label="Used since last reading"
          value={fmtUsd(current?.usage_since_reading?.cost_usd)}
          detail={
            current
              ? `${fmtTok(current.usage_since_reading.input_tokens + current.usage_since_reading.cache_read_tokens)} in · ${fmtTok(current.usage_since_reading.output_tokens)} out`
              : null
          }
        />
        <StatCard
          label="Input per 1%"
          value={perPercent ? fmtTok(perPercent.input_tokens) : "—"}
          detail="Uncached"
        />
        <StatCard
          label="Output per 1%"
          value={perPercent ? fmtTok(perPercent.output_tokens) : "—"}
        />
        <StatCard
          label="Cached input per 1%"
          value={perPercent ? fmtTok(perPercent.cache_read_tokens) : "—"}
        />
      </div>
      {current?.resets_at || current?.window_ends_at ? (
        <div className="subtle" style={{ marginTop: 10 }}>
          {current.resets_at
            ? `Window resets ${fmtTime(current.resets_at)}.`
            : `Window ends by ${fmtTime(current.window_ends_at)} at the latest.`}
        </div>
      ) : null}
    </div>
  );
}

function Readings({ readings, onDelete, busy }) {
  const { rows, pager } = usePagedRows(readings);
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Readings</h2>
        <span className="subtle">{readings.length}</span>
      </div>
      {readings.length === 0 ? (
        <div className="empty-state">
          <strong>No readings yet</strong>
          <span>Readings appear after Codex is checked.</span>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="plan-usage-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Used</th>
                <th>Resets</th>
                <th>Note</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{fmtTime(row.observed_at)}</td>
                  <td>{fmtPercent(row.used_percent)}</td>
                  <td>{row.resets_at ? fmtTime(row.resets_at) : "—"}</td>
                  <td>{row.note || ""}</td>
                  <td>
                    <button
                      className="btn ghost sm"
                      type="button"
                      disabled={busy}
                      onClick={() => onDelete(row)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {pager}
    </div>
  );
}

function Intervals({ segments }) {
  const { rows, pager } = usePagedRows(segments);
  if (!segments.length) return null;
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Measured intervals</h2>
        <span className="subtle">Usage between readings in the same window</span>
      </div>
      <div className="table-wrap">
        <table className="plan-usage-table plan-usage-table--wide">
          <thead>
            <tr>
              <th>From</th>
              <th>To</th>
              <th>Change</th>
              <th>Input</th>
              <th>Output</th>
              <th>Cached input</th>
              <th>API price</th>
              <th>Per 1%</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.start}-${row.end}`}>
                <td>
                  {row.from_window_start
                    ? `Window start ${fmtTime(row.start)}`
                    : fmtTime(row.start)}
                </td>
                <td>{fmtTime(row.end)}</td>
                <td>{fmtPercent(row.percent_change)}</td>
                <td>{fmtTok(row.usage.input_tokens)}</td>
                <td>{fmtTok(row.usage.output_tokens)}</td>
                <td>{fmtTok(row.usage.cache_read_tokens)}</td>
                <td>{fmtUsd(row.usage.cost_usd)}</td>
                <td>{fmtUsd(row.usd_per_percent)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pager}
    </div>
  );
}

export function ChatGPTPlanUsagePage() {
  const [usageWindow, setUsageWindow] = useState("weekly");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      setData(await planUsageApi.getPlanUsageSummary(usageWindow));
    } catch (e) {
      setError(e.message);
    }
  }, [usageWindow]);

  useEffect(() => {
    load();
    const timer = setInterval(load, 60_000);
    return () => clearInterval(timer);
  }, [load]);

  const remove = async (row) => {
    if (!globalThis.confirm(`Delete the ${fmtPercent(row.used_percent)} reading?`)) return;
    setBusy(true);
    try {
      await planUsageApi.deletePlanUsageReading(row.id);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const checkCodex = async () => {
    setBusy(true);
    try {
      await planUsageApi.checkPlanUsageWithCodex();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const shown = data?.window === usageWindow ? data : null;
  const codex = data?.codex;
  const noFiveHour =
    codex?.ok && !(codex.windows || []).some((item) => item.window === "five_hour");
  const windows = noFiveHour ? WINDOWS.filter((item) => item.id !== "five_hour") : WINDOWS;
  useEffect(() => {
    if (noFiveHour && usageWindow === "five_hour") setUsageWindow("weekly");
  }, [noFiveHour, usageWindow]);
  return (
    <>
      <div className="topbar">
        <div className="topbar-title">ChatGPT Plan Usage</div>
        <div className="topbar-actions">
          <button className="btn secondary" type="button" onClick={load}>
            Refresh
          </button>
        </div>
      </div>
      <div className="content scroll-content">
        <div className="page-body">
          {error && <div className="error-banner">{error}</div>}
          {windows.length > 1 ? (
            <div className="plan-usage-windows" role="tablist" aria-label="Usage window">
              {windows.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={usageWindow === item.id}
                  className={`btn ${usageWindow === item.id ? "" : "secondary"}`}
                  onClick={() => setUsageWindow(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ) : null}
          {!shown ? (
            <div className="subtle">Loading…</div>
          ) : (
            <>
              {shown.unpriced_models.length ? (
                <div className="alert warning">
                  No API price is set for {shown.unpriced_models.join(", ")}. Set prices on the{" "}
                  <a href="#/stats/usage">Usage page</a> to see dollar amounts.
                </div>
              ) : null}
              <CodexStatus
                status={shown.codex}
                usageWindow={usageWindow}
                busy={busy}
                onCheck={checkCodex}
              />
              <Summary data={shown} />
              <div className="panel">
                <div className="panel-header">
                  <h2>Usage over time</h2>
                  <span className="subtle">
                    Dots are your readings. Lines are estimates from AESPA's token use.
                  </span>
                </div>
                <UsageChart timeline={shown.timeline} readings={shown.readings} />
              </div>
              <Readings readings={shown.readings} onDelete={remove} busy={busy} />
              <Intervals segments={shown.segments} />
              <div className="subtle">
                {shown.coverage_since
                  ? `Tracking AESPA's ChatGPT plan usage since ${fmtTime(shown.coverage_since)}. Earlier usage cannot be compared with readings.`
                  : "Tracking starts when this extension is enabled."}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
