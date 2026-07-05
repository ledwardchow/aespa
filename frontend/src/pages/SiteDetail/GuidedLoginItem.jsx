import { useState, useEffect } from "react";

export function GuidedLoginItem({
  item,
  runId,
  onConfirmed
}) {
  const [browserOpen, setBrowserOpen] = useState(item.browserOpen || false);
  const [launching, setLaunching] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [err, setErr] = useState(null);
  const [copied, setCopied] = useState(false);

  // Keep in sync if parent state flips (e.g. SSE fires guided_login_browser_open)
  useEffect(() => {
    if (item.browserOpen) setBrowserOpen(true);
  }, [item.browserOpen]);
  const copyUsername = async () => {
    try {
      await navigator.clipboard.writeText(item.username);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch  {
      setErr("Clipboard unavailable — copy manually: " + item.username);
    }
  };
  const launch = async () => {
    setLaunching(true);
    setErr(null);
    try {
      await fetch(`/api/test-runs/${runId}/guided-login/${item.credential_id}/ready`, {
        method: "POST"
      });
      setBrowserOpen(true);
    } catch (e) {
      setErr(e.message);
    }
    setLaunching(false);
  };
  const confirm = async () => {
    setConfirming(true);
    setErr(null);
    try {
      await fetch(`/api/test-runs/${runId}/guided-login/${item.credential_id}/confirm`, {
        method: "POST"
      });
      onConfirmed();
    } catch (e) {
      setErr(e.message);
      setConfirming(false);
    }
  };
  if (!browserOpen) {
    return <div style={{
      display: "flex",
      alignItems: "center",
      gap: 10,
      flexWrap: "wrap"
    }}>
        <span style={{
        fontSize: 13
      }}>Login required for <strong>{item.username}</strong>. Click <strong>I'm Ready</strong> to open a browser window, then log in and come back here.</span>
        <button className="btn sm" style={{
        background: "transparent",
        border: "1px solid var(--accent)",
        color: "var(--accent)"
      }} onClick={copyUsername}>{copied ? "Copied!" : "Copy username"}</button>
        {err && <span style={{
        color: "var(--danger)",
        fontSize: 12
      }}>{err}</span>}
        <button className="btn sm" disabled={launching} onClick={launch}>{launching ? "Opening browser…" : "I'm Ready"}</button>
      </div>;
  }
  return <div style={{
    display: "flex",
    alignItems: "center",
    gap: 10,
    flexWrap: "wrap"
  }}>
      <span style={{
      fontSize: 13
    }}>Browser is open for <strong>{item.username}</strong>. Complete login (including any SSO, MFA, or push approval), then click <strong>I'm Done</strong>. Leave the browser window open, it will automatically close after credentials are captured.</span>
      {err && <span style={{
      color: "var(--danger)",
      fontSize: 12
    }}>{err}</span>}
      <button className="btn sm" disabled={confirming} onClick={confirm}>{confirming ? "Confirming…" : "I'm Done"}</button>
    </div>;
}
