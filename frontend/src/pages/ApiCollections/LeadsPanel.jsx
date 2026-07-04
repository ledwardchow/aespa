import { useState, useRef, useMemo, useReducer } from "react";
import { useRoute, nav } from "../../lib/router";
import { aliceSessionSubscribe, _aliceFlushRecovery } from "../../lib/aliceSession";
import { fmtDate, sourceLabel, markdownText, markdownCodeBlock, leadImportPayload, leadsExportFilename, leadsToMarkdown, downloadTextFile, WP_STATUS_MARK, findingImportPayload, parseFindingsMarkdownSections, markdownSection } from "../../lib/utilities";


export function LeadsPanel({
  leads,
  loading,
  emptyMsg,
  scanRunning,
  exportName
}) {
  const [expanded, setExpanded] = useState(new Set());
  const toggle = id => setExpanded(prev => {
    const n = new Set(prev);
    n.has(id) ? n.delete(id) : n.add(id);
    return n;
  });
  const onExport = () => {
    const md = leadsToMarkdown(leads, {
      runName: exportName,
      generatedAt: new Date()
    });
    downloadTextFile(leadsExportFilename(exportName), md, "text/markdown;charset=utf-8");
  };
  const sevCls = s => ({
    high: "sev-high",
    medium: "sev-medium",
    low: "sev-low",
    info: "sev-info"
  })[s] || "sev-medium";
  const statCls = s => ({
    open: "neutral",
    investigating: "warning",
    confirmed: "success",
    dismissed: "neutral",
    inconclusive: "neutral"
  })[s] || "neutral";
  if (loading) return <div className="subtle" style={{
    padding: 32,
    textAlign: "center"
  }}>Loading…</div>;
  if (!leads || leads.length === 0) return <div className="subtle" style={{
    padding: 32,
    textAlign: "center"
  }}>
      {emptyMsg || (scanRunning ? "Scan in progress — leads will appear here as they are found." : "No leads yet.")}
    </div>;
  return <div style={{
    padding: "16px 24px"
  }}>
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 8,
      marginBottom: 16,
      flexWrap: "wrap"
    }}>
      <span className="badge neutral" style={{
        fontSize: 12
      }}>{leads.length} lead{leads.length !== 1 ? "s" : ""}</span>
      {scanRunning && <span className="badge warning" style={{
        fontSize: 12
      }}>Scan running…</span>}
      <div style={{
        flex: 1
      }}></div>
      <button className="btn sm" onClick={onExport}>Export leads</button>
    </div>
    {leads.map(lead => <div key={lead.id} className="finding-card" style={{
      marginBottom: 8,
      border: "1px solid var(--border)",
      borderRadius: 8,
      overflow: "hidden"
    }}>
        <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "10px 14px",
        cursor: "pointer",
        background: "var(--surface)"
      }} onClick={() => toggle(lead.id)}>
          <span className={"sev-badge " + sevCls(lead.severity)}>{lead.severity || "medium"}</span>
          <span style={{
          fontWeight: 600,
          flex: 1
        }}>{lead.title}</span>
          {lead.category && <span className="badge neutral" style={{
          fontSize: 11
        }}>{lead.category}</span>}
          <span className={"badge " + statCls(lead.status)} style={{
          fontSize: 11
        }}>{lead.status}</span>
          <span className="badge neutral" style={{
          fontSize: 11
        }}>{Math.round((lead.confidence || 0) * 100)}% conf</span>
          <span style={{
          color: "var(--muted)",
          fontSize: 12
        }}>{expanded.has(lead.id) ? "▲" : "▼"}</span>
        </div>
        {expanded.has(lead.id) && <div style={{
        padding: "12px 14px",
        borderTop: "1px solid var(--border)",
        background: "var(--bg)"
      }}>
            {lead.location && <div style={{
          marginBottom: 8
        }}><b>Location:</b> <code style={{
            fontSize: 12
          }}>{lead.location}</code></div>}
            {lead.description && <div style={{
          marginBottom: 8
        }}><b>Description:</b>
              <div style={{
            marginTop: 4
          }}>{lead.description}</div></div>}
            {lead.evidence && <div style={{
          marginBottom: 8
        }}><b>Code evidence:</b>
              <pre style={{
            fontSize: 11,
            background: "var(--code-bg,#1e1e2e)",
            color: "var(--code-fg,#cdd6f4)",
            padding: 8,
            borderRadius: 4,
            overflow: "auto",
            maxHeight: 220,
            whiteSpace: "pre-wrap",
            marginTop: 4
          }}>{lead.evidence}</pre></div>}
            {lead.note && <div style={{
          marginBottom: 8
        }}><b>Investigation note:</b> {lead.note}</div>}
            {lead.linked_finding_id && <div style={{
          marginBottom: 8,
          color: "var(--success,#4caf50)"
        }}>
              ✔ Confirmed as <a href="#" onClick={e => {
            e.preventDefault();
          }} style={{
            color: "inherit"
          }}>Finding #{lead.linked_finding_id}</a>
            </div>}
            <div style={{
          fontSize: 11,
          color: "var(--muted)",
          marginTop: 4
        }}>
              Lead #{lead.id} · source: {lead.source || "sast"}
              {lead.investigated_by_run_id ? ` · investigated by ${lead.investigated_by_run_type || "run"} #${lead.investigated_by_run_id}` : ""}
            </div>
          </div>}
      </div>)}
  </div>;
}
