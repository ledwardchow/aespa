import { useEffect, useState } from "react";

import * as extensionsApi from "../../shared/api/extensions.js";
import { PageHeader } from "../../shared/ui/PageHeader.jsx";

function extensionStatus(extension) {
  if (!extension.enabled) return { label: "Disabled", className: "neutral" };
  if (extension.status === "failed") return { label: "Failed", className: "error" };
  const providers = [...(extension.source_providers || []), ...(extension.web_scanners || [])];
  return extension.status === "loaded" && providers.every((item) => item.availability?.available)
    ? { label: "Ready", className: "ok" }
    : { label: "Setup required", className: "neutral" };
}

export function ExtensionsPage() {
  const [extensions, setExtensions] = useState(null);
  const [error, setError] = useState(null);
  const [pendingId, setPendingId] = useState(null);

  useEffect(() => {
    extensionsApi
      .listExtensions()
      .then((items) => setExtensions(items || []))
      .catch((loadError) => setError(loadError.message));
  }, []);

  const toggleExtension = async (extension) => {
    setPendingId(extension.id);
    setError(null);
    try {
      const updated = await extensionsApi.setExtensionEnabled(extension.id, !extension.enabled);
      setExtensions((previous) =>
        previous.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (toggleError) {
      setError(toggleError.message);
    } finally {
      setPendingId(null);
    }
  };

  return (
    <>
      <PageHeader title="Extensions" />
      <div className="content scroll-content">
        {error ? (
          <div className="alert error" role="alert">
            {error}
          </div>
        ) : null}
        {extensions === null && !error ? <div className="subtle">Loading…</div> : null}
        {extensions?.length === 0 ? <div className="subtle">No extensions installed.</div> : null}
        {extensions?.length ? (
          <div className="table-wrap">
            <table>
              <colgroup>
                <col style={{ width: "29%" }} />
                <col style={{ width: "15%" }} />
                <col style={{ width: "21%" }} />
                <col style={{ width: "13%" }} />
                <col style={{ width: "22%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th>Extension</th>
                  <th>Author</th>
                  <th>Capability</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {extensions.map((extension) => {
                  const status = extensionStatus(extension);
                  return (
                    <tr key={extension.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{extension.name}</div>
                        <div className="subtle" style={{ fontSize: 12, marginTop: 2 }}>
                          {extension.id} · v{extension.version}
                        </div>
                      </td>
                      <td className="subtle">{extension.author || "—"}</td>
                      <td className="subtle">{extension.capabilities?.join(", ") || "—"}</td>
                      <td>
                        <span className={`badge ${status.className}`}>{status.label}</span>
                      </td>
                      <td>
                        <div className="row" style={{ gap: 8 }}>
                          <button
                            className="btn secondary sm"
                            type="button"
                            disabled={pendingId === extension.id}
                            onClick={() => toggleExtension(extension)}
                          >
                            {pendingId === extension.id
                              ? "Saving…"
                              : extension.enabled
                                ? "Disable"
                                : "Enable"}
                          </button>
                          <a
                            className="btn secondary sm"
                            href={`#/extensions/${encodeURIComponent(extension.id)}/settings`}
                            aria-label={`Settings for ${extension.name}`}
                          >
                            Settings
                          </a>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </>
  );
}
