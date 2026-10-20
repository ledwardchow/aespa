import * as sitesApi from "../api/sites.js";
import { useState } from "react";

import { Notice } from "../ui/Notice.jsx";

export function ScopeHostsPanel({ siteId, hosts, onChange }) {
  const [input, setInput] = useState("");
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const remove = async (host) => {
    const next = hosts.filter((h) => h !== host);
    setSaving(true);
    try {
      const result = await sitesApi.updateScopeHosts(siteId, next);
      onChange(result.scope_hosts || next);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const add = async () => {
    const host = input
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\//, "")
      .split("/")[0];
    if (!host || hosts.includes(host)) {
      setInput("");
      return;
    }
    const next = [...hosts, host];
    setSaving(true);
    try {
      const result = await sitesApi.updateScopeHosts(siteId, next);
      onChange(result.scope_hosts || next);
      setInput("");
      setAdding(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const onKey = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      add();
    } else if (e.key === "Escape") {
      setInput("");
      setAdding(false);
    }
  };
  return (
    <div className="scope-hosts-panel">
      {error && <Notice onDismiss={() => setError(null)}>{error}</Notice>}
      <div className="scope-hosts-title" title="Hosts the crawler and scanner may test">
        Scope
      </div>
      <div className="scope-hosts-list">
        {hosts.length === 0 && (
          <span className="scope-hosts-empty">No restriction — all hosts allowed</span>
        )}
        {hosts.map((h) => (
          <span key={h} className="scope-host-chip">
            {h}
            <button
              className="scope-host-remove"
              title="Remove"
              disabled={saving}
              onClick={() => remove(h)}
            >
              ×
            </button>
          </span>
        ))}
      </div>
      {adding ? (
        <div className="scope-hosts-add">
          <input
            className="scope-hosts-input"
            aria-label="Hostname and port to add"
            placeholder="api.example.com:443"
            value={input}
            onInput={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            disabled={saving}
            autoFocus
          />
          <button className="btn sm" onClick={add} disabled={saving || !input.trim()}>
            Add
          </button>
          <button
            className="btn ghost sm"
            onClick={() => {
              setInput("");
              setAdding(false);
            }}
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          className="btn ghost sm scope-hosts-add-toggle"
          aria-label="Add host to scope"
          title="Add host to scope"
          onClick={() => setAdding(true)}
        >
          +
        </button>
      )}
    </div>
  );
}
