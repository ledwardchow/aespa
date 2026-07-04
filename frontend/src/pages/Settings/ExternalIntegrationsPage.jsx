import { useState, useRef, useMemo } from "react";
import { UpstreamProxySettings } from "./UpstreamProxySettings";
import { BurpRestApiSettings } from "./BurpRestApiSettings";
import { nav } from "../../lib/router";
import { IconSites, IconApis, IconSettings, IconPlus, IconCheck, IconPlay, IconStop, IconShield, IconChevronLeft, IconChevronRight, IconBug, IconMessageSquare, IconSend, IconBrain } from "../../components/Icons";


export function ExternalIntegrationsPage() {
  const [tab, setTab] = useState("burp");
  return <>
    <div className="topbar">
      <div className="topbar-title">External Integrations</div>
    </div>
    <div className="content" style={{
      paddingLeft: 16,
      paddingRight: 0,
      paddingBottom: 0,
      display: "flex",
      flexDirection: "column",
      flex: 1,
      minHeight: 0
    }}>
      <div className="tab-bar">
        <button className={"tab-btn" + (tab === "burp" ? " active" : "")} onClick={() => setTab("burp")}>Burp Suite Integration</button>
        <button className={"tab-btn" + (tab === "proxy" ? " active" : "")} onClick={() => setTab("proxy")}>Upstream Proxy</button>
      </div>
      <div className="scroll-content" style={{
        flex: 1,
        minHeight: 0,
        overflowY: "auto",
        overflowX: "hidden",
        paddingTop: 16,
        paddingBottom: 28
      }}>
        {tab === "burp" && <BurpRestApiSettings />}
        {tab === "proxy" && <UpstreamProxySettings />}
      </div>
    </div></>;
}
