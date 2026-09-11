import React from "react";
import { IconExternalLink, IconSend } from "../../shared/ui/Icons.jsx";
import { renderAliceBlocks, renderAliceTraceBox } from "../../shared/alice/render.jsx";
import { parseAliceTurnSegments } from "../../shared/alice/segments.js";
import { renderMarkdown } from "../../shared/alice/markdown.jsx";
import { useAutoFollowScroll } from "../../shared/hooks/useAutoFollowScroll.js";
import { AliceGoalBar } from "../../shared/ui/AliceGoalBar.jsx";

/** Open the standalone A.L.I.C.E. view for a web test run. */
export function openAlicePopout(runId) {
  const url = new URL(window.location.href);
  url.hash = `#/runs/${runId}/alice-popout`;
  const name = `aespa-alice-${runId}`;
  const features = "popup,width=760,height=860,resizable=yes,scrollbars=yes";
  const popup = window.open(url.toString(), name, features);
  if (popup) {
    popup.focus();
    return popup;
  }

  // Browsers may block a popup even when this is called from a button click.
  // Try a normal new tab as a fallback.
  const tab = window.open(url.toString(), name);
  if (tab) tab.focus();
  return tab;
}

export function AliceChatPanel({
  runId,
  aliceChats,
  activeAliceTabId,
  setActiveAliceTabId,
  deleteAliceTab,
  createAliceTab,
  aliceChatHeight,
  aliceMessages,
  aliceExpandedThinkIds,
  setAliceExpandedThinkIds,
  startAliceResize,
  aliceInputText,
  setAliceInputText,
  isActiveThinking,
  aliceIsThinking = isActiveThinking,
  handleAliceSend,
  handleAliceStop,
  submitAliceDirective,
  onPopOut,
  popout = false,
}) {
  const { historyRef, handleScroll } = useAutoFollowScroll(
    activeAliceTabId,
    aliceMessages,
    isActiveThinking,
  );

  const handlePopOut = () => {
    const openedWindow = openAlicePopout(runId);
    if (openedWindow && onPopOut) onPopOut();
  };
  const activeGoal = aliceChats.find((tab) => tab.id === activeAliceTabId)?.goal;
  const sendGoalCommand = (command) => submitAliceDirective && submitAliceDirective(command);
  const editGoal = () => {
    const objective = window.prompt("Update the goal objective", activeGoal?.objective || "");
    if (objective?.trim()) sendGoalCommand(`/goal ${objective.trim()}`);
  };

  return (
    <div
      className={"alice-chat-container" + (popout ? " alice-chat-container--popout" : "")}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="alice-chat-tabs-bar">
        {aliceChats.map((tab) => {
          const isActiveTab = tab.id === activeAliceTabId;
          return (
            <div
              key={tab.id}
              className={
                "alice-chat-tab-pill" + (isActiveTab ? " alice-chat-tab-pill--active" : "")
              }
              onClick={() => setActiveAliceTabId(tab.id)}
            >
              <span>{tab.title}</span>
              <span
                className="alice-chat-tab-close"
                onClick={(e) => deleteAliceTab(tab.id, e)}
                title="Close Session"
              >
                ×
              </span>
            </div>
          );
        })}
        <button
          className="alice-chat-add-tab-btn"
          onClick={createAliceTab}
          title="New Session"
          aria-label="New Session"
        >
          +
        </button>
        {!popout && (
          <button
            className="alice-chat-popout-btn"
            onClick={handlePopOut}
            title="Open A.L.I.C.E. in a new window or tab"
            aria-label="Open A.L.I.C.E. in a new window or tab"
          >
            <IconExternalLink />
          </button>
        )}
      </div>
      <AliceGoalBar
        goal={activeGoal}
        running={aliceIsThinking}
        onPause={handleAliceStop}
        onResume={() => sendGoalCommand("/goal resume")}
        onEdit={editGoal}
        onClear={() => sendGoalCommand("/goal clear")}
      />
      <div
        className="alice-chat-history"
        style={{ height: popout ? undefined : `${aliceChatHeight}px` }}
        ref={historyRef}
        onScroll={handleScroll}
      >
        {aliceMessages.map((msg, _msgIdx) => {
          // Thinking messages render as an ordered run of trace boxes and chat bubbles.
          if (msg.type === "thinking") {
            if (!msg.text) return null;
            const segments = parseAliceTurnSegments(msg.text);
            return (
              <React.Fragment key={msg.id}>
                {segments.map((segment, segmentIndex) => {
                  if (segment.kind === "message") {
                    return (
                      <div
                        key={msg.id + ":m" + segmentIndex}
                        className="alice-msg-row alice-msg-row--alice"
                      >
                        <div className="alice-msg-bubble alice-msg-bubble--alice">
                          <div>{renderMarkdown(segment.text)}</div>
                        </div>
                      </div>
                    );
                  }
                  const segmentKey = msg.id + ":t" + segmentIndex;
                  return renderAliceTraceBox(
                    segmentKey,
                    segment.text,
                    msg.stepData || {},
                    aliceExpandedThinkIds.has(segmentKey),
                    () =>
                      setAliceExpandedThinkIds((prev) => {
                        const next = new Set(prev);
                        if (next.has(segmentKey)) next.delete(segmentKey);
                        else next.add(segmentKey);
                        return next;
                      }),
                  );
                })}
              </React.Fragment>
            );
          }
          const isUser = msg.sender === "user";
          if (!isUser && !msg.text) return null;
          return (
            <div
              key={msg.id}
              className={
                "alice-msg-row" + (isUser ? " alice-msg-row--user" : " alice-msg-row--alice")
              }
            >
              <div
                className={
                  "alice-msg-bubble" +
                  (isUser ? " alice-msg-bubble--user" : " alice-msg-bubble--alice")
                }
              >
                <div>
                  {isUser
                    ? renderMarkdown(msg.text)
                    : renderAliceBlocks(msg.text, false, msg.stepData || {})}
                </div>
                <div className="alice-msg-meta">
                  <span>{msg.ts}</span>
                </div>
              </div>
            </div>
          );
        })}
        {isActiveThinking && (
          <div className="alice-msg-row alice-msg-row--alice">
            <div className="alice-typing-bubble">
              <div className="alice-typing-dot"></div>
              <div className="alice-typing-dot"></div>
              <div className="alice-typing-dot"></div>
            </div>
          </div>
        )}
      </div>
      {!popout && <div className="alice-chat-resizer" onMouseDown={startAliceResize}></div>}
      <div className="alice-chat-input-bar">
        <input
          className="alice-chat-input"
          placeholder={
            aliceIsThinking && activeGoal?.status === "active"
              ? "Add guidance to the active goal..."
              : "Direct A.L.I.C.E., or use /goal <objective>..."
          }
          value={aliceInputText}
          disabled={aliceIsThinking && activeGoal?.status !== "active"}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleAliceSend();
            }
          }}
          onInput={(e) => setAliceInputText(e.target.value)}
        />
        {aliceIsThinking && activeGoal?.status !== "active" ? (
          <button
            className="alice-chat-stop-btn"
            onClick={handleAliceStop}
            title="Stop Generation"
            aria-label="Stop Generation"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="4" y="4" width="16" height="16" rx="1" ry="1"></rect>
            </svg>
          </button>
        ) : (
          <button
            className="alice-chat-input-btn"
            disabled={!aliceInputText.trim()}
            onClick={handleAliceSend}
            title="Send Instruction"
            aria-label="Send Instruction"
          >
            <IconSend />
          </button>
        )}
      </div>
    </div>
  );
}
