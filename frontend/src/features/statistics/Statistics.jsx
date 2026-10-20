import { fmtDate } from "../../shared/lib/dates.js";
import * as statisticsApi from "../../shared/api/statistics.js";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fmtTok } from "../../shared/ui/TokenUsageBar.jsx";
import { fmtUsd } from "../../shared/lib/money.ts";

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function localDate(value = new Date()) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function shiftDate(day, amount) {
  const [year, month, date] = day.split("-").map(Number);
  return localDate(new Date(year, month - 1, date + amount));
}

function dateLabel(day) {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(year, month - 1, date).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function weekStart(day) {
  const [year, month, date] = day.split("-").map(Number);
  const weekday = new Date(year, month - 1, date).getDay();
  return shiftDate(day, -(weekday === 0 ? 6 : weekday - 1));
}

function shiftMonth(month, amount) {
  const [year, number] = String(month).split("-").map(Number);
  const date = new Date(year, number - 1 + amount, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(month) {
  const [year, number] = String(month).split("-").map(Number);
  return new Date(year, number - 1, 1).toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });
}

function fmtCount(value) {
  return Number(value || 0).toLocaleString();
}

function providerLabel(provider) {
  const labels = {
    openrouter: "OpenRouter",
    openai: "OpenAI",
    openai_compatible: "OpenAI-compatible",
    anthropic: "Anthropic",
    google: "Google",
    google_vertex: "Google Vertex AI",
    bedrock: "Amazon Bedrock",
    bedrock_mantle: "Amazon Bedrock Mantle",
    github_copilot: "GitHub Copilot",
    factory_droid: "Factory Droid",
    claude_cli: "Claude CLI",
    openai_codex: "OpenAI Codex subscription",
    openai_chatgpt_plan: "ChatGPT plan",
    azure_openai: "Azure OpenAI",
    azure_foundry: "Azure AI Foundry",
    azure_foundry_openai: "Azure AI Foundry",
    azure_foundry_anthropic: "Azure AI Foundry",
  };
  return labels[provider] || provider;
}

function PriceEditor({ row, month, onSaved, onCancel }) {
  const p = row.prices || {};
  const [form, setForm] = useState({
    input_price_usd_per_million: p.input_usd_per_million ?? "",
    output_price_usd_per_million: p.output_usd_per_million ?? "",
    cache_read_price_usd_per_million: p.cache_read_usd_per_million ?? "",
    cache_write_price_usd_per_million: p.cache_write_usd_per_million ?? "",
    credit_price_usd_per_million: p.credit_usd_per_million ?? "",
    credit_unit: p.credit_unit || "",
    apply_to_future: true,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));
  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const payload = {
        month,
        provider: row.provider,
        model: row.model,
        service_tier: row.service_tier || "",
        ...form,
      };
      for (const key of [
        "input_price_usd_per_million",
        "output_price_usd_per_million",
        "cache_read_price_usd_per_million",
        "cache_write_price_usd_per_million",
        "credit_price_usd_per_million",
      ]) {
        if (payload[key] !== "") payload[key] = Number(payload[key]);
        else delete payload[key];
      }
      await statisticsApi.updateLLMPrices(payload);
      onSaved();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="form-section" style={{ marginTop: 10 }}>
      <div className="form-section-title">Prices per million units</div>
      <div className="form-grid two">
        {[
          ["input_price_usd_per_million", "Uncached input"],
          ["output_price_usd_per_million", "Output"],
          ["cache_read_price_usd_per_million", "Cache read"],
          ["cache_write_price_usd_per_million", "Cache write"],
          ["credit_price_usd_per_million", "Native credits"],
        ].map(([key, label]) => (
          <label key={key}>
            {label} USD / 1M
            <input
              type="number"
              min="0"
              step="any"
              value={form[key]}
              onChange={(e) => set(key, e.target.value)}
            />
          </label>
        ))}
        <label>
          Credit label
          <input
            value={form.credit_unit}
            onChange={(e) => set("credit_unit", e.target.value)}
            placeholder="credits per 1M"
          />
        </label>
      </div>
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={form.apply_to_future}
          onChange={(e) => set("apply_to_future", e.target.checked)}
        />{" "}
        Use this price for future months
      </label>
      {error && <div className="error-text">{error}</div>}
      <div className="form-actions">
        <button className="btn" onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save prices"}
        </button>
        <button className="btn ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function UsageSummary({ title, stats = {} }) {
  return (
    <div className="panel usage-summary">
      <div className="panel-header">
        <h2>{title}</h2>
        <span className="subtle">{fmtCount(stats.requests)} calls</span>
      </div>
      <div className="stats-grid">
        <div className="stat-card">
          <span>Uncached input</span>
          <strong>{fmtCount(stats.input_tokens)}</strong>
        </div>
        <div className="stat-card">
          <span>Output</span>
          <strong>{fmtCount(stats.output_tokens)}</strong>
        </div>
        <div className="stat-card">
          <span>Cache read</span>
          <strong>{fmtCount(stats.cache_read_tokens)}</strong>
        </div>
        <div className="stat-card">
          <span>Cache write</span>
          <strong>{fmtCount(stats.cache_write_tokens)}</strong>
        </div>
        <div className="stat-card">
          <span>Estimated total</span>
          <strong>{fmtUsd(stats.estimated_total_cost_usd)}</strong>
        </div>
      </div>
      {(stats.ai_credits > 0 || stats.factory_credits > 0) && (
        <div className="subtle" style={{ marginTop: 12 }}>
          Native credits:{" "}
          {stats.ai_credits > 0 ? `${fmtCount(stats.ai_credits)} Copilot AI credits` : ""}
          {stats.ai_credits > 0 && stats.factory_credits > 0 ? " · " : ""}
          {stats.factory_credits > 0 ? `${fmtCount(stats.factory_credits)} Factory credits` : ""} ·
          estimated native cost {fmtUsd(stats.estimated_credit_cost_usd)}
        </div>
      )}
    </div>
  );
}

function rowKey(row) {
  return `${row.month}:${row.provider}:${row.model}:${row.service_tier || ""}`;
}

function groupByProvider(rows) {
  const groups = new Map();
  for (const row of rows) {
    if (!groups.has(row.provider)) groups.set(row.provider, []);
    groups.get(row.provider).push(row);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => providerLabel(a).localeCompare(providerLabel(b)))
    .map(([provider, providerRows]) => ({
      provider,
      rows: providerRows.sort(
        (a, b) =>
          a.model.localeCompare(b.model) ||
          b.month.localeCompare(a.month) ||
          (a.service_tier || "").localeCompare(b.service_tier || ""),
      ),
    }));
}

function UsageTable({ provider, rows, onSaved }) {
  const [editing, setEditing] = useState(null);
  const calls = rows.reduce((sum, row) => sum + (row.requests || 0), 0);
  const pricedRows = rows.filter((row) => row.estimated_total_cost_usd != null);
  const cost = pricedRows.length
    ? pricedRows.reduce((sum, row) => sum + row.estimated_total_cost_usd, 0)
    : null;
  const missingPrices = rows.some(
    (row) => row.provider !== "google_antigravity" && row.estimated_total_cost_usd == null,
  );
  return (
    <div className="panel stats-provider-panel">
      <div className="panel-header stats-provider-header">
        <h2>{providerLabel(provider)}</h2>
        <span className="subtle">{fmtCount(calls)} calls</span>
        <div className="stats-provider-total">
          <span>Estimated cost</span>
          <strong>{provider === "google_antigravity" ? "Included" : fmtUsd(cost)}</strong>
          {missingPrices && <small>Some models have no price</small>}
        </div>
      </div>
      <div className="table-wrap">
        <table className="stats-table">
          <colgroup>
            <col className="stats-provider-col" />
            <col className="stats-calls-col" />
            <col className="stats-token-col" />
            <col className="stats-token-col" />
            <col className="stats-token-col" />
            <col className="stats-token-col" />
            <col className="stats-credit-col" />
            <col className="stats-cost-col" />
            <col className="stats-action-col" />
          </colgroup>
          <thead>
            <tr>
              <th>Model</th>
              <th>Calls</th>
              <th>Input</th>
              <th>Output</th>
              <th>Cache read</th>
              <th>Cache write</th>
              <th>Native credits</th>
              <th>Cost</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <React.Fragment key={rowKey(row)}>
                <tr>
                  <td>
                    <div className="mono">{row.model}</div>
                    <div className="subtle">{monthLabel(row.month)}</div>
                    {row.service_tier && (
                      <span className="stats-tier-label">
                        {["fast", "priority"].includes(row.service_tier)
                          ? "Fast mode"
                          : row.service_tier}
                      </span>
                    )}
                    {row.base_url && (
                      <div className="mono subtle stats-base-url" title={row.base_url}>
                        {row.base_url}
                      </div>
                    )}
                  </td>
                  <td>{fmtCount(row.requests)}</td>
                  <td>{fmtTok(row.input_tokens)}</td>
                  <td>{fmtTok(row.output_tokens)}</td>
                  <td>{fmtTok(row.cache_read_tokens)}</td>
                  <td>{fmtTok(row.cache_write_tokens)}</td>
                  <td>
                    {row.ai_credits > 0
                      ? `${fmtCount(row.ai_credits)} Copilot`
                      : row.factory_credits > 0
                        ? `${fmtCount(row.factory_credits)} Factory`
                        : "—"}
                  </td>
                  <td title={row.prices?.confidence || ""}>
                    {row.provider === "google_antigravity"
                      ? "Included"
                      : fmtUsd(row.estimated_total_cost_usd)}
                  </td>
                  <td>
                    {row.provider === "google_antigravity" ? (
                      <span className="subtle">Included</span>
                    ) : (
                      <button
                        className="btn ghost sm"
                        onClick={() => setEditing(editing === rowKey(row) ? null : rowKey(row))}
                      >
                        Prices
                      </button>
                    )}
                  </td>
                </tr>
                {editing === rowKey(row) && (
                  <tr>
                    <td colSpan="9">
                      <PriceEditor
                        row={row}
                        month={row.month}
                        onSaved={() => {
                          setEditing(null);
                          onSaved();
                        }}
                        onCancel={() => setEditing(null)}
                      />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function StatisticsPage() {
  const [view, setView] = useState("monthly");
  const [month, setMonth] = useState(currentMonth);
  const [day, setDay] = useState(localDate);
  const [start, setStart] = useState(localDate);
  const [end, setEnd] = useState(localDate);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const requestId = useRef(0);

  const selection = useMemo(() => {
    if (view === "monthly") return { view, month };
    if (view === "weekly" || view === "daily") return { view, date: day };
    if (view === "custom") return { view, start, end };
    return { view };
  }, [view, month, day, start, end]);
  const invalidRange = view === "custom" && (!start || !end || start > end);

  const load = useCallback(async () => {
    const id = ++requestId.current;
    if (invalidRange) {
      setData(null);
      setError(null);
      return;
    }
    try {
      setError(null);
      const result = await statisticsApi.getLLMStatistics(selection);
      if (id === requestId.current) setData(result);
    } catch (e) {
      if (id === requestId.current) {
        setData(null);
        setError(e.message);
      }
    }
  }, [selection, invalidRange]);
  useEffect(() => {
    load();
  }, [load]);

  const months = useMemo(() => {
    const values = new Set([month, currentMonth(), ...(data?.available_months || [])]);
    return [...values].sort().reverse();
  }, [data, month]);

  const refresh = async () => {
    setBusy(true);
    setError(null);
    try {
      await statisticsApi.refreshLLMPrices();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    if (
      !window.confirm(
        "Reset all LLM statistics? Every stored month will be permanently cleared. Downloaded and manual prices will be kept.",
      )
    )
      return;
    setBusy(true);
    setError(null);
    try {
      await statisticsApi.resetLLMStatistics();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const rows = data?.rows || [];
  const providers = groupByProvider(rows);
  const totals = data?.totals || {};
  const periodLabel =
    view === "all_time"
      ? "All-time"
      : view === "monthly"
        ? monthLabel(month)
        : view === "daily"
          ? dateLabel(day)
          : view === "weekly"
            ? `${dateLabel(weekStart(day))} - ${dateLabel(shiftDate(weekStart(day), 6))}`
            : start && end
              ? `${dateLabel(start)} - ${dateLabel(end)}`
              : "Custom range";
  return (
    <>
      <div className="topbar">
        <div className="topbar-title">Usage</div>
        <div className="topbar-actions">
          <button className="btn secondary" onClick={refresh} disabled={busy}>
            {busy ? "Working…" : "Refresh prices"}
          </button>
          <button className="btn danger" onClick={reset} disabled={busy}>
            Reset statistics
          </button>
        </div>
      </div>
      <div className="content scroll-content">
        <div className="page-body">
          {error && <div className="error-banner">{error}</div>}
          <div className="panel stats-period-panel">
            <div className="stats-period-toolbar">
              <div className="stats-view-tabs" role="group" aria-label="Usage period">
                {[
                  ["all_time", "All-time"],
                  ["monthly", "Monthly"],
                  ["weekly", "Weekly"],
                  ["daily", "Daily"],
                  ["custom", "Custom"],
                ].map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    className="stats-view-button"
                    aria-pressed={view === value}
                    onClick={() => setView(value)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {view === "monthly" && (
                <div className="stats-period-controls">
                  <button
                    className="btn ghost stats-period-arrow"
                    aria-label="Previous month"
                    onClick={() => setMonth((m) => shiftMonth(m, -1))}
                  >
                    ‹
                  </button>
                  <select
                    value={month}
                    onChange={(e) => setMonth(e.target.value)}
                    aria-label="Statistics month"
                  >
                    {months.map((value) => (
                      <option key={value} value={value}>
                        {monthLabel(value)}
                      </option>
                    ))}
                  </select>
                  <button
                    className="btn ghost stats-period-arrow"
                    aria-label="Next month"
                    onClick={() => setMonth((m) => shiftMonth(m, 1))}
                  >
                    ›
                  </button>
                </div>
              )}
              {(view === "weekly" || view === "daily") && (
                <div className="stats-period-controls">
                  <button
                    className="btn ghost stats-period-arrow"
                    aria-label={`Previous ${view === "weekly" ? "week" : "day"}`}
                    onClick={() => setDay((d) => shiftDate(d, view === "weekly" ? -7 : -1))}
                  >
                    ‹
                  </button>
                  <label>
                    {view === "weekly" ? "Week containing" : "Date"}
                    <input type="date" value={day} onChange={(e) => setDay(e.target.value)} />
                  </label>
                  <button
                    className="btn ghost stats-period-arrow"
                    aria-label={`Next ${view === "weekly" ? "week" : "day"}`}
                    onClick={() => setDay((d) => shiftDate(d, view === "weekly" ? 7 : 1))}
                  >
                    ›
                  </button>
                </div>
              )}
              {view === "custom" && (
                <div className="stats-period-controls">
                  <label>
                    Start date
                    <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
                  </label>
                  <label>
                    End date
                    <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
                  </label>
                  {invalidRange && (
                    <span className="error-text">
                      Choose an end date on or after the start date.
                    </span>
                  )}
                </div>
              )}
              <span className="subtle stats-price-meta">
                Price data:{" "}
                {data?.price_feed?.fetched_at
                  ? fmtDate(data.price_feed.fetched_at)
                  : "not downloaded"}
              </span>
            </div>
          </div>
          {view !== "all_time" && view !== "monthly" && data?.legacy_months?.length > 0 && (
            <div className="stats-history-note">
              Older usage in {data.legacy_months.map(monthLabel).join(", ")} was saved by month only
              and is not included in this date range. See Monthly or All-time for those totals.
            </div>
          )}
          <UsageSummary title={periodLabel} stats={totals} />
          {providers.length === 0 ? (
            <div className="panel empty-state">
              <strong>
                {invalidRange
                  ? "Choose a valid date range"
                  : `No usage recorded for ${periodLabel}`}
              </strong>
              <span>LLM calls will appear here as they complete.</span>
            </div>
          ) : (
            providers.map(({ provider, rows: providerRows }) => (
              <UsageTable key={provider} provider={provider} rows={providerRows} onSaved={load} />
            ))
          )}
        </div>
      </div>
    </>
  );
}
