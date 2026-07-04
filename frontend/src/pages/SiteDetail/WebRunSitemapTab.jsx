import React from "react";
import { IconPlay } from "../../components/Icons";
export function WebRunSitemapTab(props) {
  const { activeTab, run, onStart, onStartThinkingScan, hasCheckpoint, onResumeThinkingScan, checkpointStatus } = props;
  return (
    <>
      {activeTab === "sitemap" && run?.status === "pending" ? <div style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 12
            }}>
                    <span>Ready to crawl.</span>
                    <button className="btn" onClick={onStart}><IconPlay /> Start crawl</button>
                    <span className="subtle" style={{
                fontSize: 12
              }}>or</span>
                    <button className="btn" onClick={onStartThinkingScan}><IconPlay /> Start Dynamic Scan</button>
                    {hasCheckpoint && <button className="btn" style={{
                background: "var(--warn)",
                color: "#000",
                borderColor: "var(--warn)"
              }} onClick={onResumeThinkingScan}><IconPlay /> Resume Pentest (step {checkpointStatus.step_count})</button>}
                  </div> : <span>No pages discovered yet.</span>}
    </>
  );
}
