import * as applicationsApi from "../../shared/api/applications.js";
import { useState, useEffect, useRef } from "react";

import { campaignDisplayWarnings } from "../../shared/runs/campaignPresentation.js";

const MAX_ENTRIES = 300;
// If the stream is truly silent (a genuinely empty activity history), no
// onmessage ever fires — heartbeat frames are SSE comment lines, invisible
// to EventSource's onmessage. This is just how long "loading" waits before
// settling on "no activity yet" rather than spinning forever.
const INITIAL_LOAD_TIMEOUT_MS = 3000;

// Normalizes one CampaignActivityEntry — the same shape whether it arrived
// as part of the stream's initial history replay or as a newly-persisted
// row, since /activity/stream serves both through one identical feed.
function normalizeEntry(e, fallbackId) {
  const eventId = e.event_id || null;
  return {
    id: eventId ? `id:${eventId}` : fallbackId,
    eventId,
    ts: e.timestamp,
    type: e.type,
    status: e.status,
    role: e.role || null,
    phase: e.phase || null,
    message: e.message || null,
    task: e.task || null,
    outcome: e.outcome || null,
  };
}

// ── CampaignActivityTab ──────────────────────────────────────────────────────
// Uses the cursor-safe GET .../campaigns/{id}/activity/stream endpoint —
// backed entirely by re-polling AgentLog/ScanLog server-side, so it replays
// full persisted history and then keeps following new rows through the same
// feed with no fetch→subscribe gap at all (the plain /events pub/sub stream
// is deliberately left unused for this tab; it has no history and no
// cursor). Every entry carries a stable `event_id` ("<agent_wm>.<scan_wm>"),
// so dedup is a permanent id Set rather than a fingerprint/window heuristic.
// `lastEventIdRef` is passed back as `?cursor=` on (re)connect — including
// across React StrictMode's dev-only double effect invocation — so a
// reconnect never re-replays entries already rendered.
export function CampaignActivityTab({ applicationId, campaignId, campaign }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [streaming, setStreaming] = useState(true);
  const lastStatusRef = useRef(null);
  const lastEventIdRef = useRef(null);
  const localIdCounter = useRef(0);
  // Deliberately a ref, not a per-effect-invocation local Set: it must
  // survive React StrictMode's dev-only cleanup+remount so an old
  // connection's still-in-flight messages and the new connection's replay
  // are deduped against each other too, not just within one invocation.
  const seenIdsRef = useRef(new Set());

  useEffect(() => {
    let cancelled = false;

    const addEntry = (normalized) => {
      if (seenIdsRef.current.has(normalized.id)) return;
      seenIdsRef.current.add(normalized.id);
      if (normalized.eventId) lastEventIdRef.current = normalized.eventId;
      setLoading(false);
      setEntries((prev) => [...prev, normalized].slice(-MAX_ENTRIES));
    };

    const url = applicationsApi.getCampaignActivityStreamUrl(
      applicationId,
      campaignId,
      lastEventIdRef.current,
    );
    const es = new EventSource(url);
    es.onopen = () => setStreaming(true);
    es.onmessage = (e) => {
      try {
        const evt = JSON.parse(e.data);
        localIdCounter.current += 1;
        addEntry(normalizeEntry(evt, `local:${localIdCounter.current}`));
      } catch {
        /* heartbeat comment lines never reach onmessage */
      }
    };
    es.onerror = () => setStreaming(false);

    // Only resolves "no activity at all" — a real entry always flips
    // loading off immediately via addEntry, well before this fires.
    const initialTimer = setTimeout(() => {
      if (!cancelled) setLoading(false);
    }, INITIAL_LOAD_TIMEOUT_MS);

    return () => {
      cancelled = true;
      clearTimeout(initialTimer);
      es.close();
    };
  }, [applicationId, campaignId]);

  // Fallback: while the stream is down, synthesize entries from status
  // polls already driven by the parent's useCampaign hook (campaign prop
  // updates) so the tab still shows forward progress. /events is
  // deliberately not used here — this lighter synthetic trail is enough.
  useEffect(() => {
    if (streaming || !campaign) return;
    if (lastStatusRef.current === campaign.status) return;
    lastStatusRef.current = campaign.status;
    localIdCounter.current += 1;
    setEntries((prev) =>
      [
        ...prev,
        {
          id: `local:${localIdCounter.current}`,
          eventId: null,
          ts: new Date().toISOString(),
          type: "status_poll",
          status: campaign.status,
          task: `Campaign status: ${campaign.status}`,
        },
      ].slice(-MAX_ENTRIES),
    );
  }, [streaming, campaign]);

  const warnings = campaignDisplayWarnings(campaign);

  return (
    <div>
      <div className="row spread" style={{ marginBottom: 10 }}>
        <span className="subtle">
          {entries.length} event{entries.length !== 1 ? "s" : ""}
        </span>
        {!streaming && (
          <span className="badge warning">
            Live stream unavailable — showing status-poll fallback
          </span>
        )}
      </div>
      {warnings.length > 0 && (
        <div className="alert warning" style={{ marginBottom: 12 }}>
          {warnings.map((w, i) => (
            <div key={i}>{w}</div>
          ))}
        </div>
      )}
      {loading ? (
        <div className="subtle" style={{ padding: 24, textAlign: "center" }}>
          Loading…
        </div>
      ) : entries.length === 0 ? (
        <div className="subtle" style={{ padding: 24, textAlign: "center" }}>
          No activity recorded yet. Activity appears here as the campaign runs, and reloading this
          page replays everything recorded so far.
        </div>
      ) : (
        <div className="activity-feed">
          {entries.map((e) => (
            <div key={e.id} className="activity-entry">
              <span className="activity-ts">
                {new Date(e.ts).toLocaleTimeString("en-US", { hour12: false })}
              </span>
              <span className="activity-badge phase-other">
                {(e.status || e.type || "").toUpperCase()}
              </span>
              <span className="activity-msg">
                {e.task || e.message || ""}
                {e.outcome ? ` → ${e.outcome}` : ""}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
