import React from "react";

export function fmtTok(n) {
  if (!n || n <= 0) return "0";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

export function fmtCredits(n) {
  const value = Number(n || 0);
  if (value >= 100) return value.toFixed(1);
  if (value >= 1) return value.toFixed(2);
  return value.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}

export function TokenUsageBar({ tokenUsage, tokenExpanded, setTokenExpanded }) {
  const hasTokens = tokenUsage && (tokenUsage.total_input > 0 || tokenUsage.total_output > 0);
  const providers = new Set(Object.values(tokenUsage?.by_model || {}).map(v => v.provider));
  const hasCopilot = providers.has("github_copilot");
  const hasDroid = providers.has("factory_droid");
  const hasProviderUsage = hasCopilot || hasDroid;
  const hasBilledUsage = tokenUsage && (
    tokenUsage.total_ai_credits > 0 ||
    tokenUsage.total_factory_credits > 0 ||
    tokenUsage.total_premium_requests > 0
  );
  const hasUsage = hasTokens || hasProviderUsage;
  const usageLabel = hasDroid && !hasCopilot ? "Droid usage" : hasCopilot && !hasDroid ? "Copilot usage" : "LLM usage";
  const quota = tokenUsage?.copilot_quota;

  return (
    <>
      <div
        className="activity-token-bar"
        onClick={hasUsage ? () => setTokenExpanded?.(p => !p) : undefined}
        style={{ cursor: hasUsage ? "pointer" : "default" }}
      >
        {hasUsage ? (
          <>
            <span className="token-bar-label">{hasProviderUsage ? usageLabel : "Tokens"}</span>
            {tokenUsage.total_factory_credits > 0 ? (
              <span className="token-bar-in" title="Factory Droid credits used by this run">
                {fmtTok(tokenUsage.total_factory_credits)} Droid credits
              </span>
            ) : null}
            {tokenUsage.total_ai_credits > 0 ? (
              <span className="token-bar-in" title="GitHub AI credits used by this run">
                {tokenUsage.total_factory_credits > 0 ? <span className="token-bar-sep">·</span> : null}
                {fmtCredits(tokenUsage.total_ai_credits)} AI credits
              </span>
            ) : null}
            {tokenUsage.total_premium_requests > 0 ? (
              <>
                {tokenUsage.total_factory_credits > 0 || tokenUsage.total_ai_credits > 0 ? <span className="token-bar-sep">·</span> : null}
                <span className="token-bar-in" title="Legacy Copilot premium requests used by this run">
                  {fmtCredits(tokenUsage.total_premium_requests)} premium requests
                </span>
              </>
            ) : null}
            {hasProviderUsage ? (
              <>
                {hasBilledUsage ? <span className="token-bar-sep">·</span> : null}
                <span className="token-bar-out" title="Model calls made by this run">
                  {fmtTok(tokenUsage.total_requests)} calls
                </span>
              </>
            ) : null}
            {hasTokens ? (
              <>
                {hasProviderUsage ? <span className="token-bar-sep">·</span> : null}
                <span className="token-bar-in" title="Input tokens">
                  ↑{fmtTok(tokenUsage.total_input)} in
                </span>
                <span className="token-bar-sep">·</span>
                <span className="token-bar-out" title="Output tokens">
                  ↓{fmtTok(tokenUsage.total_output)} out
                </span>
              </>
            ) : null}
            {tokenUsage.total_cache_read > 0 || tokenUsage.total_cache_write > 0 ? (
              <>
                <span className="token-bar-sep">·</span>
                {tokenUsage.total_cache_read > 0 ? (
                  <span className="token-bar-cache-read" title="Cache read tokens">
                    ⚡{fmtTok(tokenUsage.total_cache_read)} cached
                  </span>
                ) : null}
                {tokenUsage.total_cache_write > 0 ? (
                  <span className="token-bar-cache-write" title="Cache write tokens">
                    ✎{fmtTok(tokenUsage.total_cache_write)} written
                  </span>
                ) : null}
              </>
            ) : null}
            <span className="activity-expand-chevron" style={{ marginLeft: 4 }}>
              {tokenExpanded ? "▲" : "▼"}
            </span>
          </>
        ) : (
          <span className="token-bar-empty">No usage data yet</span>
        )}
      </div>
      {tokenExpanded && hasUsage && (
        <div className="token-breakdown">
          {quota && Number.isFinite(Number(quota.remaining_percentage)) ? (
            <div className="token-breakdown-row">
              <span className="token-model-name">Copilot allowance</span>
              <span className="token-in">{Number(quota.remaining_percentage).toFixed(0)}% remaining</span>
              {quota.reset_at ? (
                <span className="token-out" title={quota.reset_at}>
                  resets {new Date(quota.reset_at).toLocaleDateString()}
                </span>
              ) : null}
            </div>
          ) : null}
          {Object.entries(tokenUsage.by_model || {}).map(([model, v]) => (
            <div key={model} className="token-breakdown-row">
              <span className="token-model-name">{model}</span>
              {v.factory_credits > 0 ? <span className="token-in">{fmtTok(v.factory_credits)} Droid credits</span> : null}
              {v.ai_credits > 0 ? <span className="token-in">{fmtCredits(v.ai_credits)} credits</span> : null}
              {v.premium_requests > 0 ? <span className="token-in">{fmtCredits(v.premium_requests)} premium</span> : null}
              {v.requests > 0 ? <span className="token-out">{fmtTok(v.requests)} calls</span> : null}
              {v.input > 0 ? <span className="token-in">↑{fmtTok(v.input)}</span> : null}
              {v.output > 0 ? <span className="token-out">↓{fmtTok(v.output)}</span> : null}
              {v.cache_read > 0 || v.cache_write > 0 ? (
                <>
                  {v.cache_read > 0 ? (
                    <span className="token-cache-read" title="Cache read">
                      ⚡{fmtTok(v.cache_read)}
                    </span>
                  ) : null}
                  {v.cache_write > 0 ? (
                    <span className="token-cache-write" title="Cache write">
                      ✎{fmtTok(v.cache_write)}
                    </span>
                  ) : null}
                </>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
