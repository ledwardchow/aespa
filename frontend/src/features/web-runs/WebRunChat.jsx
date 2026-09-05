import { createContext, useContext, useEffect, useState } from "react";
import { useAliceChat } from "./useAliceChat.js";
const WebRunChat = createContext(null);

export function WebRunChatProvider({ runId, children }) {
  const [collapsedAgentIds, setCollapsedAgentIds] = useState(new Set());
  const toggleAgentId = (aid) =>
    setCollapsedAgentIds((prev) => {
      const next = new Set(prev);
      if (next.has(aid)) next.delete(aid);
      else next.add(aid);
      return next;
    });
  const chat = useAliceChat(runId, {
    onActivate: () =>
      setCollapsedAgentIds((prev) => {
        if (!prev.has("alice")) return prev;
        const next = new Set(prev);
        next.delete("alice");
        return next;
      }),
  });
  const { setAliceChats, setActiveAliceTabId } = chat;
  useEffect(() => {
    const reopenAlicePanel = () => {
      setCollapsedAgentIds((prev) => {
        if (!prev.has("alice")) return prev;
        const next = new Set(prev);
        next.delete("alice");
        return next;
      });
    };
    const applyAlicePopoutState = (data) => {
      if (Array.isArray(data?.chats)) setAliceChats(data.chats);
      if (data?.active_tab_id) setActiveAliceTabId(data.active_tab_id);
      reopenAlicePanel();
    };
    const handleAlicePopoutClose = (event) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== "aespa-alice-popout-close" || Number(event.data.runId) !== runId)
        return;
      applyAlicePopoutState(event.data);
    };
    const handleAlicePopoutStorage = (event) => {
      if (event.key !== `aespa-alice-popout-close:${runId}`) return;
      try {
        applyAlicePopoutState(JSON.parse(event.newValue || "null"));
      } catch {}
    };
    window.addEventListener("message", handleAlicePopoutClose);
    window.addEventListener("storage", handleAlicePopoutStorage);
    return () => {
      window.removeEventListener("message", handleAlicePopoutClose);
      window.removeEventListener("storage", handleAlicePopoutStorage);
    };
  }, [runId, setActiveAliceTabId, setAliceChats]);
  return (
    <WebRunChat.Provider value={{ ...chat, collapsedAgentIds, toggleAgentId }}>
      {children}
    </WebRunChat.Provider>
  );
}
export function useWebRunChat() {
  const value = useContext(WebRunChat);
  if (!value) throw new Error("Chat requires a web run provider");
  return value;
}
