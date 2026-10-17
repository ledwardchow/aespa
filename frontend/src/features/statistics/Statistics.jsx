import { fmtDate } from "../../shared/lib/dates.js";
import * as statisticsApi from "../../shared/api/statistics.js";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import { fmtTok } from "../../shared/ui/TokenUsageBar.jsx";
import { fmtUsd } from "../../shared/lib/money.ts";

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
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

function UsageSummary({ title, stats = {}, headerContent }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
        <span className="subtle">{fmtCount(stats.requests)} calls</span>
        {headerContent}
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
  return `${row.provider}:${row.model}:${row.service_tier || ""}`;
}

function UsageTable({ title, rows, month, emptyState, onSaved }) {
  const [editing, setEditing] = useState(null);
  const calls = rows.reduce((sum, row) => sum + (row.requests || 0), 0);
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
        <span className="subtle">{fmtCount(calls)} calls</span>
      </div>
      {rows.length === 0 ? (
        emptyState
      ) : (
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
                <th>Provider / model</th>
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
                      <div>{providerLabel(row.provider)}</div>
                      <div className="mono subtle">{row.model}</div>
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
                          month={month}
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
      )}
    </div>
  );
}

export function StatisticsPage() {
  const [month, setMonth] = useState(currentMonth);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      setData(await statisticsApi.getLLMStatistics(month));
    } catch (e) {
      setError(e.message);
    }
  }, [month]);
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
  const standardRows = rows.filter((row) => !row.service_tier);
  const fastRows = rows.filter((row) => row.service_tier);
  const totals = data?.totals || {};
  const lifetime = data?.lifetime || {};
  const monthlyHeader = (
    <>
      <span className="stats-month-controls">
        <button className="btn ghost" onClick={() => setMonth((m) => shiftMonth(m, -1))}>
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
        <button className="btn ghost" onClick={() => setMonth((m) => shiftMonth(m, 1))}>
          ›
        </button>
      </span>
      <span className="subtle stats-price-meta">
        Price data:{" "}
        {data?.price_feed?.fetched_at ? fmtDate(data.price_feed.fetched_at) : "not downloaded"}
      </span>
    </>
  );
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
          <UsageSummary
            title="Lifetime"
            stats={lifetime}
            headerContent={
              <span className="subtle stats-summary-meta">
                {fmtCount(lifetime.months)} month{lifetime.months === 1 ? "" : "s"}
              </span>
            }
          />
          <UsageSummary
            title={`Monthly · ${monthLabel(month)}`}
            stats={totals}
            headerContent={monthlyHeader}
          />
          {(standardRows.length > 0 || fastRows.length === 0) && (
            <UsageTable
              title="Provider and model breakdown"
              rows={standardRows}
              month={month}
              onSaved={load}
              emptyState={
                <div className="empty-state">
                  <strong>No usage recorded for {monthLabel(month)}</strong>
                  <span>LLM calls will appear here as they complete.</span>
                </div>
              }
            />
          )}
          {fastRows.length > 0 && (
            <UsageTable title="Fast mode" rows={fastRows} month={month} onSaved={load} />
          )}
        </div>
      </div>
    </>
  );
}
