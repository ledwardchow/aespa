import { GuidedLoginItem } from "./GuidedLoginItem";

export function GuidedLoginNotices({ runId, pending, errors, onDismissError, onConfirmed }) {
  return <>
    {errors.length > 0 && <div style={{ background: "var(--surface-2,#2a2a2a)", border: "2px solid var(--danger)", borderRadius: 6, padding: "12px 16px", marginBottom: 12, display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ fontWeight: 600, fontSize: 13, color: "var(--danger)" }}>⚠️ Guided Browser Login Failed</div>
      {errors.map(error => <div key={error.credential_id} style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}><span style={{ fontSize: 13 }}>{error.message}</span><button className="btn sm ghost" onClick={() => onDismissError(error.credential_id)}>Dismiss</button></div>)}
    </div>}
    {pending.length > 0 && <div style={{ background: "var(--surface-2,#2a2a2a)", border: "2px solid var(--warn,#f59e0b)", borderRadius: 6, padding: "12px 16px", marginBottom: 12, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontWeight: 600, fontSize: 13, color: "var(--warn,#f59e0b)" }}>🖥️ Guided Login Required</div>
      {pending.map(item => <GuidedLoginItem key={item.credential_id} item={item} runId={runId} onConfirmed={() => onConfirmed(item.credential_id)} />)}
    </div>}
  </>;
}
