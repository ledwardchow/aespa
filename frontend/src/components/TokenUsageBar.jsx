import React from "react";

export function fmtTok(n) {
  if (!n || n <= 0) return "0";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

export function TokenUsageBar({ tokenUsage, tokenExpanded, setTokenExpanded }) {
  const hasTokens = tokenUsage && (tokenUsage.total_input > 0 || tokenUsage.total_output > 0);

  return (
    <>
      <div
        className="activity-token-bar"
        onClick={hasTokens ? () => setTokenExpanded?.(p => !p) : undefined}
        style={{ cursor: hasTokens ? "pointer" : "default" }}
      >
        {hasTokens ? (
          <>
            <span className="token-bar-label">Tokens</span>
            <span className="token-bar-in" title="Input tokens">
              ↑{fmtTok(tokenUsage.total_input)} in
            </span>
            <span className="token-bar-sep">·</span>
            <span className="token-bar-out" title="Output tokens">
              ↓{fmtTok(tokenUsage.total_output)} out
            </span>
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
          <span className="token-bar-empty">No token data yet</span>
        )}
      </div>
      {tokenExpanded && hasTokens && (
        <div className="token-breakdown">
          {Object.entries(tokenUsage.by_model || {}).map(([model, v]) => (
            <div key={model} className="token-breakdown-row">
              <span className="token-model-name">{model}</span>
              <span className="token-in">↑{fmtTok(v.input)}</span>
              <span className="token-out">↓{fmtTok(v.output)}</span>
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
