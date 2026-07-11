import { useState } from "react";
import { truncUrl } from "../../lib/utilities";

export function AttackSurfacePanel({
  summary
}) {
  const [expanded, setExpanded] = useState({
    trust_zones: true,
    attack_classes: true,
    meta: false
  });
  const toggle = key => setExpanded(prev => ({
    ...prev,
    [key]: !prev[key]
  }));
  const priorityTone = p => p >= 88 ? "high" : p >= 78 ? "medium" : "low";
  if (!summary) {
    return <div className="attack-surface-empty">
        <span className="subtle">No attack surface summary yet. Run a Dynamic Scan to generate one.</span>
      </div>;
  }
  const {
    trust_zones = {},
    attack_classes = [],
    tech_stack = [],
    credential_roles = [],
    entry_points = []
  } = summary;
  const zoneEntries = Object.entries(trust_zones).filter(([, urls]) => urls?.length > 0);
  return <div className="attack-surface-panel">

        <div className="attack-surface-section">
          <div className="attack-surface-section-head" onClick={() => toggle("trust_zones")}>
            <span className="attack-surface-toggle">{expanded.trust_zones ? "▾" : "▸"}</span>
            <span className="attack-surface-section-title">Trust Zones</span>
            {zoneEntries.map(([zone, urls]) => <span key={zone} className={"zone-badge zone-" + zone}>{zone.toUpperCase()} ({urls.length})</span>)}
          </div>
          {expanded.trust_zones && <div className="attack-surface-body">
              {zoneEntries.map(([zone, urls]) => <div key={zone} className="trust-zone-group">
                  <div className={"trust-zone-label zone-" + zone}>{zone.toUpperCase()}</div>
                  <div className="trust-zone-urls">
                    {urls.slice(0, 8).map(url => <div key={url} className="mono trust-zone-url" title={url}>{truncUrl(url, 90)}</div>)}
                    {urls.length > 8 && <div className="subtle">+{urls.length - 8} more</div>}
                  </div>
                </div>)}
            </div>}
        </div>

        <div className="attack-surface-section">
          <div className="attack-surface-section-head" onClick={() => toggle("attack_classes")}>
            <span className="attack-surface-toggle">{expanded.attack_classes ? "▾" : "▸"}</span>
            <span className="attack-surface-section-title">Attack Classes</span>
            <span className="subtle">{attack_classes.length} identified</span>
          </div>
          {expanded.attack_classes && <div className="attack-surface-body">
              {attack_classes.map(cls => {
          const urls = cls.entry_point_urls || [];
          return <div key={cls.id} className="attack-class-card">
                    <div className="attack-class-head">
                      <span className={"task-priority " + priorityTone(cls.priority)}>P{cls.priority}</span>
                      <span className="owasp-badge">{cls.owasp}</span>
                      <span className="attack-class-id">{cls.id?.replace(/_/g, " ")}</span>
                    </div>
                    <div className="attack-class-rationale">{cls.rationale}</div>
                    {urls.length > 0 && <div className="attack-class-urls">
                        {urls.slice(0, 4).map(url => <span key={url} className="mono attack-class-url" title={url}>{truncUrl(url, 70)}</span>)}
                        {urls.length > 4 && <span className="subtle">+{urls.length - 4} more</span>}
                      </div>}
                  </div>;
        })}
            </div>}
        </div>

        <div className="attack-surface-section">
          <div className="attack-surface-section-head" onClick={() => toggle("meta")}>
            <span className="attack-surface-toggle">{expanded.meta ? "▾" : "▸"}</span>
            <span className="attack-surface-section-title">Tech Stack & Credentials</span>
          </div>
          {expanded.meta && <div className="attack-surface-body">
              {tech_stack.length > 0 && <div className="meta-row">
                  <span className="meta-label">Tech stack:</span>
                  {tech_stack.map(t => <span key={t} className="intel-kind">{t}</span>)}
                </div>}
              {credential_roles.length > 0 && <div className="meta-row">
                  <span className="meta-label">Credential roles:</span>
                  {credential_roles.map(r => <span key={r} className="intel-kind">{r}</span>)}
                </div>}
              <div className="meta-row">
                <span className="meta-label">Entry points:</span>
                <span>{entry_points.length} total</span>
              </div>
            </div>}
        </div>

    </div>;
}