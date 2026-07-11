import { useState } from "react";
import { api } from "../../lib/api";


export function ScopeHostsPanel({
  siteId,
  hosts,
  onChange
}) {
  const [input, setInput] = useState("");
  const [saving, setSaving] = useState(false);
  const remove = async host => {
    const next = hosts.filter(h => h !== host);
    setSaving(true);
    try {
      await api.updateScopeHosts(siteId, next);
      onChange(next);
    } catch (e) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };
  const add = async () => {
    const host = input.trim().toLowerCase().replace(/^https?:\/\//, "").split("/")[0];
    if (!host || hosts.includes(host)) {
      setInput("");
      return;
    }
    const next = [...hosts, host];
    setSaving(true);
    try {
      await api.updateScopeHosts(siteId, next);
      onChange(next);
      setInput("");
    } catch (e) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };
  const onKey = e => {
    if (e.key === "Enter") {
      e.preventDefault();
      add();
    }
  };
  return <div className="scope-hosts-panel">
      <div className="scope-hosts-title">Attack Scope</div>
      <div className="scope-hosts-list">
        {hosts.length === 0 && <span className="scope-hosts-empty">No restriction — all hosts allowed</span>}
        {hosts.map(h => <span key={h} className="scope-host-chip">
            {h}
            <button className="scope-host-remove" title="Remove" disabled={saving} onClick={() => remove(h)}>×</button>
          </span>)}
      </div>
      <div className="scope-hosts-add">
        <input className="scope-hosts-input" placeholder="Add hostname…" value={input} onInput={e => setInput(e.target.value)} onKeyDown={onKey} disabled={saving} />
        <button className="btn sm" onClick={add} disabled={saving || !input.trim()}>Add</button>
      </div>
    </div>;
}
