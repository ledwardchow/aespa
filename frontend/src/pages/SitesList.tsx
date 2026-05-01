import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, SiteSummary } from "../api";

function IconPlus() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  );
}

export default function SitesList() {
  const [sites, setSites] = useState<SiteSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try { setSites(await api.listSites()); }
    catch (e) { setError((e as Error).message); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onDelete = async (s: SiteSummary) => {
    if (!confirm(`Delete "${s.name}"? This also removes its credentials.`)) return;
    try { await api.deleteSite(s.id); await load(); }
    catch (e) { setError((e as Error).message); }
  };

  const authCount = sites ? sites.filter((s) => s.requires_auth).length : 0;
  const credCount = sites ? sites.reduce((n, s) => n + s.credential_count, 0) : 0;

  return (
    <>
      <div className="topbar">
        <div className="topbar-title">Sites</div>
        <div className="topbar-actions">
          <button className="btn" onClick={() => navigate("/sites/new")}>
            <IconPlus /> New site
          </button>
        </div>
      </div>

      <div className="content">
        {error && <div className="alert error" style={{ marginBottom: 16 }}>{error}</div>}

        {sites && sites.length > 0 && (
          <div className="stat-strip">
            <div className="stat">
              <span className="stat-value">{sites.length}</span>
              <span className="stat-label">Sites</span>
            </div>
            <div className="stat">
              <span className="stat-value">{authCount}</span>
              <span className="stat-label">Authenticated</span>
            </div>
            <div className="stat">
              <span className="stat-value">{credCount}</span>
              <span className="stat-label">Credentials</span>
            </div>
          </div>
        )}

        {sites === null && <div className="subtle">Loading…</div>}

        {sites !== null && sites.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">⬡</div>
            <div className="empty-msg">No sites configured</div>
            <div className="empty-sub">Add a target site to begin setting up your pentest scope.</div>
            <button className="btn" onClick={() => navigate("/sites/new")}>
              <IconPlus /> New site
            </button>
          </div>
        )}

        {sites && sites.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Base URL</th>
                  <th>Auth</th>
                  <th>Credentials</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sites.map((s) => (
                  <tr key={s.id}>
                    <td><strong>{s.name}</strong></td>
                    <td className="url">{s.base_url}</td>
                    <td>
                      {s.requires_auth
                        ? <span className="badge ok">required</span>
                        : <span className="badge neutral">none</span>}
                    </td>
                    <td>
                      {s.credential_count > 0
                        ? s.credential_count
                        : <span className="subtle">—</span>}
                    </td>
                    <td>
                      <div className="row" style={{ justifyContent: "flex-end" }}>
                        <button className="btn secondary sm" onClick={() => navigate(`/sites/${s.id}`)}>
                          Edit
                        </button>
                        <button className="btn danger-outline sm" onClick={() => onDelete(s)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
