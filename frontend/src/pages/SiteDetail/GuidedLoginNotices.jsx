import { GuidedLoginItem } from "./GuidedLoginItem";

export function GuidedLoginNotices({ runId, pending, errors, entraPrompts = [], interactiveLogins = [], onDismissError, onDismissEntraPrompt, onRetryEntraPrompt, onConfirmed }) {
  const status = entraPrompts[0]?.status;
  const entraTone = status === "success" ? "var(--success,#22c55e)" : status === "timeout" || status === "retry_required" ? "var(--danger)" : "var(--accent)";
  const entraTitle = status === "success" ? "Microsoft Authenticator Confirmed" : status === "timeout" ? "Microsoft Authenticator Timed Out" : status === "retry_required" ? "Microsoft Authenticator Failed" : "Microsoft Authenticator Approval";
  const interactiveNames = interactiveLogins.map(item => `${item.mode} for ${item.label || item.username}`).join(", ");
  return <>
    {interactiveLogins.length > 0 && <div style={{ background: "var(--surface-2,#2a2a2a)", border: "1px solid var(--warn,#f59e0b)", borderRadius: 6, padding: "10px 14px", marginBottom: 12, color: "var(--text-2)", fontSize: 13 }}>
      This run includes interactive login: <strong style={{ color: "var(--text)" }}>{interactiveNames}</strong>. Keep this page open; AESPA will show Authenticator, guided browser, retry, and confirmation prompts here when human input is needed.
    </div>}
    {entraPrompts.length > 0 && <div style={{ background: "var(--surface-2,#2a2a2a)", border: `2px solid ${entraTone}`, borderRadius: 6, padding: "12px 16px", marginBottom: 12, display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ fontWeight: 600, fontSize: 13, color: entraTone }}>{entraTitle}</div>
      {entraPrompts.map(prompt => <div key={prompt.id} style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}><span style={{ fontSize: 13 }}>{prompt.message || <>Attempting Entra login as <strong>{prompt.username}</strong> - open Authenticator and enter <strong>{prompt.number}</strong></>}</span>{prompt.status === "retry_required" && <button className="btn sm" onClick={() => onRetryEntraPrompt(prompt)}>Retry</button>}<button className="btn sm ghost" onClick={() => onDismissEntraPrompt(prompt.id)}>Dismiss</button></div>)}
    </div>}
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
