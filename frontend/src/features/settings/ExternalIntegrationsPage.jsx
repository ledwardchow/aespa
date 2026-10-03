import { UpstreamProxySettings } from "./UpstreamProxySettings.jsx";

export function ExternalIntegrationsPage() {
  return (
    <>
      <div className="topbar">
        <div className="topbar-title">External Integrations</div>
      </div>
      <div className="content" style={{ padding: 16, flex: 1, minHeight: 0, overflowY: "auto" }}>
        <UpstreamProxySettings />
      </div>
    </>
  );
}
