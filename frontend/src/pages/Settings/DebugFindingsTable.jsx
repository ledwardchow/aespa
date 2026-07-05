import { renderMarkdown } from "../../lib/aliceSession";
import { useState, useRef, useMemo } from "react";
import { nav } from "../../lib/router";
import { IconSites, IconApis, IconSettings, IconPlus, IconCheck, IconPlay, IconStop, IconShield, IconChevronLeft, IconChevronRight, IconBug, IconMessageSquare, IconSend, IconBrain } from "../../components/Icons";


export function DebugFindingsTable({
  findings
}) {
  const [expandedFinding, setExpandedFinding] = useState(null);
  const SEV_ORDER = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3,
    info: 4
  };
  const sorted = [...findings].sort((a, b) => (SEV_ORDER[a.severity] ?? 99) - (SEV_ORDER[b.severity] ?? 99));
  return <div className="findings-table-wrap">
      <table className="findings-table" style={{
      tableLayout: "fixed",
      width: "100%"
    }}>
        <colgroup><col style={{
          width: 80
        }} /><col /></colgroup>
        <thead>
          <tr><th>Sev</th><th>Title</th></tr>
        </thead>
        <tbody>
          {sorted.map((f, idx) => <>
            <tr key={idx} className="finding-group-row" onClick={() => setExpandedFinding(expandedFinding === idx ? null : idx)}>
              <td><span className={"sev-badge sev-" + (f.severity || "info")}>{f.severity || "info"}</span></td>
              <td className="finding-title" style={{
              width: "100%"
            }}>
                <div className="row" style={{
                alignItems: "flex-start",
                gap: 8
              }}>
                  <div style={{
                  flex: 1,
                  minWidth: 0
                }}>
                    <span className="group-chevron">{expandedFinding === idx ? "▾" : "▸"}</span>
                    {f.title || "Untitled finding"}
                    <div className="mono" style={{
                    fontSize: 11,
                    wordBreak: "break-all",
                    marginTop: 4
                  }}>{f.affected_url || ""}</div>
                  </div>
                  {f.cvss_score != null && <span className="subtle" style={{
                  whiteSpace: "nowrap",
                  fontSize: 11,
                  paddingTop: 2
                }}>{f.cvss_score}</span>}
                </div>
              </td>
            </tr>
            {expandedFinding === idx && <tr className="finding-evidence-row">
                <td colSpan="2">
                  <div className="finding-description">
                    <div><strong>Description</strong></div><div>{renderMarkdown(f.description) || "—"}</div>
                    <div style={{
                  marginTop: 8
                }}><strong>Impact</strong></div><div>{renderMarkdown(f.impact) || "—"}</div>
                    <div style={{
                  marginTop: 8
                }}><strong>Likelihood</strong></div><div>{renderMarkdown(f.likelihood) || "—"}</div>
                    <div style={{
                  marginTop: 8
                }}><strong>Recommendation</strong></div><div>{renderMarkdown(f.recommendation) || "—"}</div>
                    <div style={{
                  marginTop: 8
                }}><strong>CVSS 3.1</strong></div>
                    <div>{f.cvss_score ?? "—"} {f.cvss_vector && <span className="mono" style={{
                    marginLeft: 8,
                    fontSize: 11
                  }}>{f.cvss_vector}</span>}</div>
                  </div>
                  {f.evidence && <pre className="finding-evidence">{f.evidence}</pre>}
                </td>
              </tr>}
          </>)}
        </tbody>
      </table>
    </div>;
}