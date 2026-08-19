import { useRef } from "react";
import { api } from "../../lib/api";
import { truncUrl } from "../../lib/utilities";
import { isDynamicScanActive } from "./_helpers";
import { runStatusFromThinkingStatus } from "./runState";
import { useEventStream } from "../../hooks/useEventStream";

const isHidden404Node = node => (
  node?.status === "failed"
  && String(node.error_message || "").trim().toUpperCase() === "HTTP 404"
);

export function useWebRunEvents(options) {
  const { runId, setGraph, setCrawlUsername, setRun, setCrawlStopRequested, setAgents, upsertAgent, setThinkingStatus, setThinkingStopReq, setActivityLog, setSitePlanData, setFindings, setValidateStatus, setValidateBusy, setTokenUsage, setScopeHosts, setGuidedLoginPending, setGuidedLoginErrors, setEntraPrompts, setCheckpointStatus } = options;

  const pageAnalysisStatusMapRef = useRef(new Map());

  // SSE: receive incremental graph + status updates — no graph polling needed.
  useEventStream(`/api/test-runs/${runId}/events`, {
    onMessage: msg => {
      let evt;
      try {
        evt = JSON.parse(msg.data);
      } catch {
        return;
      }
      if (evt.type === "page_added") {
        setGraph(prev => {
          if (!prev) return prev;
          const exists = prev.nodes.some(n => n.id === evt.node.id);
          if (exists) return prev;
          const cachedStatus = pageAnalysisStatusMapRef.current.get(evt.node.id);
          const node = {
            ...evt.node,
            accessible_by: evt.node.accessible_by || [],
            accessible_anonymously: !!evt.node.accessible_anonymously,
            analysis_status: cachedStatus || evt.node.analysis_status || (evt.node.status === "redirect" ? "skipped" : evt.node.context ? "complete" : "pending")
          };
          if (isHidden404Node(node)) return prev;
          const newLinks = evt.link ? [...prev.links, evt.link] : prev.links;
          return {
            nodes: [...prev.nodes, node],
            links: newLinks
          };
        });
      } else if (evt.type === "crawl_phase") {
        setCrawlUsername(evt.username || null);
      } else if (evt.type === "node_accessible_by") {
        api.getGraph(runId).then(setGraph).catch(() => {});
      } else if (evt.type === "page_updated") {
        setGraph(prev => {
          if (!prev) return prev;
          const updatedNode = prev.nodes.find(n => n.id === evt.page_id);
          const nextNode = updatedNode ? {
            ...updatedNode,
            status: evt.status ?? updatedNode.status,
            error_message: evt.error_message ?? updatedNode.error_message,
            state_label: evt.state_label || updatedNode.state_label,
            context: evt.llm_context || updatedNode.context,
            req_auth: evt.req_auth ?? updatedNode.req_auth,
            takes_input: evt.takes_input ?? updatedNode.takes_input,
            has_object_ref: evt.has_object_ref ?? updatedNode.has_object_ref,
            has_business_logic: evt.has_business_logic ?? updatedNode.has_business_logic,
            owasp_applicable: evt.owasp_applicable || updatedNode.owasp_applicable,
            analysis_status: evt.analysis_status
              || (evt.status === "redirect" ? "skipped" : evt.llm_context ? "complete" : updatedNode.analysis_status)
          } : null;
          if (isHidden404Node(nextNode)) {
            return {
              nodes: prev.nodes.filter(n => n.id !== evt.page_id),
              links: prev.links.filter(link => link.source !== evt.page_id && link.target !== evt.page_id)
            };
          }
          return {
            ...prev,
            nodes: prev.nodes.map(n => n.id === evt.page_id ? nextNode : n)
          };
        });
      } else if (evt.type === "llm_analysis_progress") {
        setRun(prev => prev ? {
          ...prev,
          llm_pending: evt.pending_count,
          llm_completed: evt.completed_count
        } : prev);
        if (evt.page_id && evt.status) {
          pageAnalysisStatusMapRef.current.set(evt.page_id, evt.status);
          setGraph(prev => {
            if (!prev) return prev;
            return {
              ...prev,
              nodes: prev.nodes.map(n => n.id === evt.page_id ? {
                ...n,
                analysis_status: evt.status
              } : n)
            };
          });
        }
      } else if (evt.type === "run_update") {
        setRun(prev => prev ? {
          ...prev,
          status: evt.status ?? prev.status,
          phase: evt.phase ?? prev.phase,
          pages_discovered: evt.pages_discovered ?? prev.pages_discovered,
          llm_pending: evt.status && evt.status !== "running" ? 0 : prev.llm_pending
        } : prev);
        if (evt.status && evt.status !== "running") {
          setCrawlStopRequested(false);
          pageAnalysisStatusMapRef.current.clear();
          api.getGraph(runId).then(setGraph).catch(() => {});
        }
        if (evt.username !== undefined) setCrawlUsername(evt.username || null);
      } else if (evt.type === "crawl_progress") {
        const ts = new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        });
        setAgents(prev => {
          const username = evt.username || "anonymous";
          const crawlEvent = {
            ts,
            username,
            url: evt.current_url || "",
            pagesVisited: evt.pages_visited || 0,
            done: !!evt.done,
            stage: evt.stage || (evt.done ? "phase_complete" : "page_visit"),
            stageLabel: evt.stage_label || (evt.done ? "Credential phase complete" : "Opening page"),
            phaseIndex: evt.phase_index,
            phaseTotal: evt.phase_total
          };
          const idx = prev.findIndex(a => a.id === "crawler");
          const existingEvents = idx >= 0 ? prev[idx].crawlEvents || [] : [];
          const crawlEvents = [...existingEvents, crawlEvent].slice(-200);
          const phaseLabel = evt.phase_index && evt.phase_total ? `Phase ${evt.phase_index}/${evt.phase_total} · ` : "";
          const currentTask = evt.done
            ? `${phaseLabel}Completed crawl as ${username} (${evt.pages_visited || 0} pg)`
            : `${phaseLabel}${evt.stage_label || "Opening page"} · ${username}: ${truncUrl(evt.current_url || "", 88)}`;
          return upsertAgent(prev, {
            id: "crawler",
            role: "Crawler",
            status: "active",
            currentTask,
            crawlEvents
          });
        });
        // crawl_progress is still used for the done flag
        if (evt.username && evt.done) {
          setRun(prev => {
            if (!prev) return prev;
            const pup = {
              ...(prev.per_user_progress || {})
            };
            pup[evt.username] = {
              ...pup[evt.username],
              done: true
            };
            return {
              ...prev,
              per_user_progress: pup
            };
          });
        }
      } else if (evt.type === "node_scan_status") {
        setGraph(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            nodes: prev.nodes.map(n => n.id === evt.page_id ? {
              ...n,
              scan_status: evt.scan_status
            } : n)
          };
        });
      } else if (evt.type === "thinking_scan_update") {
        setThinkingStatus(evt);
        // Keep the header's phase/outcome/reason badges live during the dynamic
        // scan — these fields on `run` are otherwise only refreshed by the
        // initial load or the crawl-only poll, so they'd get stuck once the
        // scan phase started.
        setRun(prev => prev ? {
          ...prev,
          status: runStatusFromThinkingStatus(evt, prev.status),
          phase: evt.run_phase ?? prev.phase,
          outcome: evt.run_outcome ?? prev.outcome,
          terminal_reason: evt.run_terminal_reason ?? prev.terminal_reason
        } : prev);
        if (evt.status && !isDynamicScanActive(evt.status)) {
          setThinkingStopReq(false);
          if (setCheckpointStatus) {
            api.getCheckpointStatus(runId).then(setCheckpointStatus).catch(() => {});
          }
        }
      } else if (evt.type === "scanner_phase") {
        setActivityLog(prev => {
          const ts = new Date().toLocaleTimeString("en-US", {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
          });
          const entry = {
            ...evt,
            _ts: ts,
            _id: Date.now() + Math.random()
          };
          const next = [...prev, entry];
          return next.length > 500 ? next.slice(-500) : next;
        });
        if (evt.phase === "site_plan" && evt.status === "complete" && evt.data) {
          setSitePlanData(evt.data);
        }
      } else if (evt.type === "finding_validation_update") {
        setFindings(prev => prev.map(f => f.id === evt.finding_id ? {
          ...f,
          validation_status: evt.validation_status ?? f.validation_status,
          validation_note: evt.validation_note ?? f.validation_note,
          evidence_json: evt.evidence_json ?? f.evidence_json,
          evidence_items: evt.evidence_items ?? f.evidence_items,
          poc_command: evt.poc_command ?? f.poc_command,
          poc_setup: evt.poc_setup ?? f.poc_setup
        } : f));
        // Refresh validation status summary when an individual finding resolves.
        api.getValidateStatus(runId).then(vs => {
          setValidateStatus(vs);
          if (vs.status !== "running") {
            setValidateBusy(false);
            api.getFindings(runId).then(setFindings).catch(() => {});
          }
        }).catch(() => {});
      } else if (evt.type === "validation_status_update") {
        setValidateStatus(evt);
        if (evt.status !== "running") {
          setValidateBusy(false);
          api.getFindings(runId).then(setFindings).catch(() => {});
        }
      } else if (evt.type === "agent_status") {
        const ts = new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        });
        setAgents(prev => {
          const histEntry = {
            ts,
            task: evt.current_task,
            outcome: evt.outcome
          };
          return upsertAgent(prev, {
            id: evt.agent_id,
            role: evt.role,
            status: evt.status,
            currentTask: evt.current_task,
            outcome: evt.outcome,
            findingReference: evt.finding_reference
          }, histEntry);
        });
      } else if (evt.type === "specialist_step") {
        const ts = new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        });
        const agentId = evt.agent_id;
        if (agentId) {
          setAgents(prev => {
            const idx = prev.findIndex(a => a.id === agentId);
            const stepEntry = {
              ts,
              step: evt.step,
              action_type: evt.action_type,
              method: evt.method,
              url: evt.url,
              status: evt.status,
              observation: evt.observation
            };
            if (idx === -1) return prev;
            const updated = [...prev];
            const prev_agent = updated[idx];
            updated[idx] = {
              ...prev_agent,
              stepHistory: [...(prev_agent.stepHistory || []), stepEntry].slice(-200)
            };
            return updated;
          });
        }
      } else if (evt.type === "token_usage_update") {
        setTokenUsage(evt.totals);
      } else if (evt.type === "scope_hosts_updated") {
        setScopeHosts(evt.scope_hosts || []);
      } else if (evt.type === "guided_login_required") {
        setGuidedLoginPending(prev => {
          if (prev.some(p => p.credential_id === evt.credential_id)) return prev;
          return [...prev, {
            credential_id: evt.credential_id,
            username: evt.username,
            browserOpen: false
          }];
        });
      } else if (evt.type === "guided_login_browser_open") {
        setGuidedLoginPending(prev => prev.map(p => p.credential_id === evt.credential_id ? {
          ...p,
          browserOpen: true
        } : p));
      } else if (evt.type === "guided_login_failed") {
        setGuidedLoginErrors(prev => {
          if (prev.some(e => e.credential_id === evt.credential_id)) return prev;
          return [...prev, {
            credential_id: evt.credential_id,
            username: evt.username,
            message: evt.message
          }];
        });
        setGuidedLoginPending(prev => prev.filter(p => p.credential_id !== evt.credential_id));
      } else if (evt.type === "guided_login_confirmed") {
        setGuidedLoginPending(prev => prev.filter(p => p.credential_id !== evt.credential_id));
      } else if (evt.type === "entra_authenticator_prompt") {
        setEntraPrompts(prev => {
          const id = `${evt.credential_id || evt.username || "entra"}:${evt.number || ""}`;
          const prompt = {
            id,
            credential_id: evt.credential_id,
            username: evt.username,
            number: evt.number,
            status: "pending",
            message: evt.message
          };
          const next = [prompt, ...prev.filter(p => p.id !== id && p.credential_id !== evt.credential_id)];
          return next.slice(0, 3);
        });
      } else if (evt.type === "entra_authenticator_status") {
        setEntraPrompts(prev => {
          const id = `${evt.credential_id || evt.username || "entra"}:${evt.status || "status"}`;
          const prompt = {
            id,
            credential_id: evt.credential_id,
            username: evt.username,
            number: evt.number,
            status: evt.status || "info",
            message: evt.message
          };
          const next = [prompt, ...prev.filter(p => p.id !== id && p.credential_id !== evt.credential_id)];
          return next.slice(0, 3);
        });
      }
    }
  });
}
