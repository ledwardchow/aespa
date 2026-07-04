import { useState, useEffect, useCallback, useContext } from "react";
import { api, formatError } from "../../lib/api";
import { SCAN_MODE_OPTIONS, SCAN_MODE_DEFINITIONS, ScanModeDefinitions, scanModeLabel, csv, defaultPolicyForm, policyToForm, policyPayload } from "../../lib/policy";
import { aliceSessionSubscribe, _aliceFlushRecovery } from "../../lib/aliceSession";
import { IconSites, IconApis, IconSettings, IconPlus, IconCheck, IconPlay, IconStop, IconShield, IconChevronLeft, IconChevronRight, IconBug, IconMessageSquare, IconSend, IconBrain } from "../../components/Icons";


export function ApiRunEndpointsTab({
  runId,
  run
}) {
  const [endpoints, setEndpoints] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!run) return;
    api.listApiEndpoints(run.collection_id).then(data => {
      setEndpoints(data || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [run]);
  if (loading) return <div className="subtle" style={{
    padding: 24
  }}>Loading endpoints…</div>;
  if (!endpoints.length) return <div className="subtle" style={{
    padding: 24,
    textAlign: "center"
  }}>
      No endpoints found. Upload and parse API documentation first.
    </div>;
  const parsedNotes = ep => {
    try {
      return JSON.parse(ep.prereq_notes || "[]");
    } catch {
      return [];
    }
  };
  const readinessIcon = ok => ok ? <span style={{
    color: "var(--success,#4caf50)"
  }}>✔</span> : <span style={{
    color: "var(--danger,#f44336)"
  }}>✘</span>;
  return <div style={{
    padding: "16px"
  }}>
      <h3 style={{
      marginBottom: 12
    }}>Endpoint Prerequisites</h3>
      <table className="data-table" style={{
      width: "100%",
      borderCollapse: "collapse"
    }}>
        <thead>
          <tr>
            <th>Method</th><th>Path</th><th>Auth Req.</th>
            <th title="Enough info to probe this endpoint">Testable?</th>
            <th title="Have credentials for auth-required paths">Auth Testable?</th>
            <th>Notes / Gaps</th>
          </tr>
        </thead>
        <tbody>
          {endpoints.map(ep => {
          const notes = parsedNotes(ep);
          return <tr key={ep.id}>
                <td><span className={"method-badge method-" + ep.method.toLowerCase()}>{ep.method}</span></td>
                <td className="mono" style={{
              fontSize: 12
            }}>{ep.path}</td>
                <td style={{
              textAlign: "center"
            }}>{ep.auth_required ? <span className="badge warning">Auth</span> : <span className="badge neutral">Open</span>}</td>
                <td style={{
              textAlign: "center"
            }}>{readinessIcon(ep.prereq_can_test)}</td>
                <td style={{
              textAlign: "center"
            }}>{readinessIcon(ep.prereq_can_test_auth)}</td>
                <td style={{
              fontSize: 11,
              color: notes.length ? "var(--danger,#f44336)" : "var(--muted)"
            }}>
                  {notes.length ? notes.join(" · ") : "—"}
                </td>
              </tr>;
        })}
        </tbody>
      </table>
    </div>;
}

// ── ApiRunWorkProgramTab — coverage matrix + live updates ─────────────────────

export const OWASP_LABELS = {
  API1: "BOLA",
  API2: "Broken Auth",
  API3: "BOPLA",
  API4: "Consumption",
  API5: "BFLA",
  API6: "Bus. Flows",
  API7: "SSRF",
  API8: "Misconfig",
  API9: "Inventory",
  API10: "Ext. APIs"
};
export const COVERAGE_CATEGORIES = ["API1", "API2", "API3", "API4", "API5", "API6", "API7", "API8", "API9", "API10"];

export const OWASP_WEB_SHORT = {
  A01: "Access Control",
  A02: "Crypto Failures",
  A03: "Injection",
  A04: "Insecure Design",
  A05: "Misconfig",
  A06: "Supply Chain",
  A07: "Auth Failures",
  A08: "Data Integrity",
  A09: "Logging & Mon.",
  A10: "SSRF"
};
