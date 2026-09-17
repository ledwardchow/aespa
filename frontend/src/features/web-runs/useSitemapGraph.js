import { useCallback, useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { truncUrl } from "../../shared/lib/urls.js";
import { getSitemapGravity } from "../../shared/lib/sitemapPreferences.js";
import { markSiteEntries } from "./sitemapRootLayout.js";
import { scopeColor, userColor } from "../../shared/runs/presentation.jsx";

const needsLlmAnalysis = (node) =>
  node &&
  node.status !== "failed" &&
  node.status !== "redirect" &&
  node.analysis_status !== "complete" &&
  node.analysis_status !== "skipped" &&
  (node.analysis_status === "pending" || !node.context);

const isApiLaneNode = (node) => node.isApiGroup || node.isApiNode;
const isGroupedNode = (node) => node.isApiGroup || node.isPageGroup || node.isDiscoveryGroup;

// Owns the imperative D3 lifecycle while TestRunDetail keeps the selected-node
// state and the page-detail actions that depend on it.
export function useSitemapGraph({
  searchMatches,
  site,
  graph,
  activeTab,
  graphView,
  credentials,
  currentUrl,
  layoutMode = "force",
  selectedNodeId,
  onSelectNode,
}) {
  const svgRef = useRef(null);
  const simulationRef = useRef(null);
  const previousStructureKeyRef = useRef("");
  const [gravity, setGravity] = useState(getSitemapGravity);
  const gravityRef = useRef(gravity);

  useEffect(() => {
    gravityRef.current = gravity;
  }, [gravity]);

  // Debug settings writes the slider value to the same localStorage key from
  // another tab/window; pick it up live rather than requiring a remount.
  useEffect(() => {
    const onStorage = () => setGravity(getSitemapGravity());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const nodeColor = useCallback(
    (node) => {
      if (graphView === "user") return userColor(node, credentials);
      return scopeColor(node);
    },
    [credentials, graphView],
  );

  useEffect(() => {
    if (!graph || !svgRef.current) return;
    const nodeStructure = graph.nodes.map((node) => node.id).join(",");
    const linkStructure = graph.links
      .map((link) => {
        const source = typeof link.source === "object" ? link.source?.id : link.source;
        const target = typeof link.target === "object" ? link.target?.id : link.target;
        return `${source}>${target}`;
      })
      .join(",");
    const structureKey = `${activeTab}:${graphView}:${layoutMode}:${JSON.stringify([site?.base_url, site?.login_url, site?.credentials?.map((item) => item.login_url)])}:${nodeStructure}:${linkStructure}`;

    // Status-only updates retain the settled simulation and repaint in place.
    if (structureKey === previousStructureKeyRef.current && simulationRef.current) {
      const simulationNodes = simulationRef.current.nodes();
      graph.nodes.forEach((updatedNode) => {
        const simulationNode = simulationNodes.find((node) => node.id === updatedNode.id);
        if (simulationNode) Object.assign(simulationNode, updatedNode);
      });
      d3.select(svgRef.current)
        .selectAll("circle.node-dot")
        .filter((node) => node && node.id != null)
        .attr("fill", nodeColor)
        .attr("stroke", (node) => (node.status === "failed" ? "#fbbf24" : "var(--bg)"));
      d3.select(svgRef.current)
        .selectAll("g.node-group")
        .each(function (nodeData) {
          if (!nodeData) return;
          const g = d3.select(this);
          g.selectAll(".node-llm-pulse").remove();
          if (needsLlmAnalysis(nodeData)) {
            g.insert("circle", ":first-child").attr("class", "node-llm-pulse").attr("r", 10);
          }
        });
      return;
    }

    previousStructureKeyRef.current = structureKey;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    const nodes = graph.nodes.map((node) => ({ ...node }));
    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = graph.links
      .filter((link) => {
        const s = typeof link.source === "object" ? link.source?.id : link.source;
        const t = typeof link.target === "object" ? link.target?.id : link.target;
        return nodeIds.has(s) && nodeIds.has(t);
      })
      .map((link) => ({ ...link }));
    const graphGroup = svg.append("g");
    const zoom = d3
      .zoom()
      .scaleExtent([0.2, 4])
      .on("zoom", (event) => graphGroup.attr("transform", event.transform));
    svg.call(zoom);

    svg
      .append("defs")
      .append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -4 8 8")
      .attr("refX", 18)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-4L8,0L0,4")
      .attr("fill", "var(--border-2)");
    const link = graphGroup
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "var(--border-2)")
      .attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrow)");
    const linkCount = graphGroup
      .append("g")
      .selectAll("text")
      .data(links.filter((item) => item.count > 1))
      .join("text")
      .attr("class", "graph-link-count")
      .attr("text-anchor", "middle")
      .attr("fill", "var(--muted)")
      .attr("font-size", "10px")
      .attr("pointer-events", "none")
      .text((item) => `×${item.count}`);
    markSiteEntries(nodes, site);
    const width = svgRef.current.clientWidth || 800;
    const height = svgRef.current.clientHeight || 500;
    const simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink(links)
          .id((node) => node.id)
          .distance(layoutMode === "api-lanes" ? 150 : 110)
          .strength(0.8),
      )
      .force("charge", d3.forceManyBody().strength(layoutMode === "api-lanes" ? -450 : -350))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "x",
        d3
          .forceX((item) =>
            layoutMode === "api-lanes" ? width * (isApiLaneNode(item) ? 0.76 : 0.28) : width / 2,
          )
          .strength(layoutMode === "api-lanes" ? 0.28 : gravityRef.current),
      )
      .force("y", d3.forceY(height / 2).strength(gravityRef.current))
      .force(
        "collision",
        d3.forceCollide((item) => (isGroupedNode(item) ? 34 : 22)),
      );
    const node = graphGroup
      .append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("class", "node-group")
      .attr("cursor", "pointer")
      .call(
        d3
          .drag()
          .on("start", (event, draggedNode) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            draggedNode.fx = draggedNode.x;
            draggedNode.fy = draggedNode.y;
          })
          .on("drag", (event, draggedNode) => {
            draggedNode.fx = event.x;
            draggedNode.fy = event.y;
          })
          .on("end", (event, draggedNode) => {
            if (!event.active) simulation.alphaTarget(0);
            draggedNode.fx = null;
            draggedNode.fy = null;
          }),
      )
      .on("click", (event, clickedNode) => {
        event.stopPropagation();
        onSelectNode(clickedNode);
      });

    node.each(function (nodeData) {
      if (!nodeData) return;
      if (needsLlmAnalysis(nodeData)) {
        d3.select(this)
          .insert("circle", ":first-child")
          .attr("class", "node-llm-pulse")
          .attr("r", 10);
      }
    });

    node
      .append("circle")
      .attr("class", "node-dot")
      .attr("r", (item) => (item.isSiteEntry ? 18 : isGroupedNode(item) ? 15 : 10))
      .attr("fill", nodeColor)
      .attr("stroke", (node) => (node.status === "failed" ? "#fbbf24" : "var(--bg)"))
      .attr("stroke-width", 2);
    node
      .filter(isGroupedNode)
      .append("text")
      .attr("class", "api-node-count")
      .attr("dy", 4)
      .attr("text-anchor", "middle")
      .attr("fill", "white")
      .attr("font-size", "10px")
      .attr("font-weight", "700")
      .attr("pointer-events", "none")
      .text((item) => item.variantCount ?? item.discoveryCount);
    const rootNode = nodes.find((node) => node.depth === 0);
    let baseHost = null;
    try {
      if (rootNode) baseHost = new URL(rootNode.url).host;
    } catch {}
    node
      .append("text")
      .attr("dy", (item) => (isGroupedNode(item) ? 30 : 22))
      .attr("text-anchor", "middle")
      .attr("fill", "var(--muted)")
      .attr("font-size", "10px")
      .attr("pointer-events", "none")
      .text((node) => {
        if (node.isDiscoveryGroup) return "Direct scan discoveries";
        if (node.isApiGroup) return `${node.apiMethod} ${node.apiPath}`;
        if (node.isPageGroup) return node.routePath;
        try {
          const url = new URL(node.url);
          const address =
            url.host === baseHost ? url.pathname + url.search + url.hash || "/" : node.url;
          const label = node.state_label || address;
          return label.length > 36 ? label.slice(0, 35) + "…" : label;
        } catch {
          return truncUrl(node.url, 36);
        }
      });
    node
      .filter((item) => item.entryRole)
      .append("text")
      .attr("class", "sitemap-entry-label")
      .attr("y", -28)
      .attr("text-anchor", "middle")
      .attr("fill", "var(--text)")
      .attr("font-size", 11)
      .attr("font-weight", 600)
      .text((item) => item.entryRole);
    node.append("title").text((node) => {
      if (node.isDiscoveryGroup) {
        return `${node.discoveryCount} routes observed without a recorded source page`;
      }
      const err =
        node.status === "failed" && node.error_message
          ? `\n(Failed: ${node.error_message})`
          : node.status === "failed"
            ? "\n(Failed)"
            : "";
      return node.state_label ? `${node.url}\n${node.state_label}${err}` : `${node.url}${err}`;
    });
    svg.on("click", () => onSelectNode(null));
    const render = () => {
      link
        .attr("x1", (node) => node.source.x)
        .attr("y1", (node) => node.source.y)
        .attr("x2", (node) => node.target.x)
        .attr("y2", (node) => node.target.y);
      node.attr("transform", (node) => `translate(${node.x},${node.y})`);
      linkCount
        .attr("x", (item) => (item.source.x + item.target.x) / 2)
        .attr("y", (item) => (item.source.y + item.target.y) / 2 - 5);
    };
    simulation.on("tick", render);
    simulation.tick();
    render();
    simulationRef.current = simulation;
    const observer = new window.ResizeObserver(() => {
      const width = svgRef.current?.clientWidth;
      const height = svgRef.current?.clientHeight;
      if (!width || !height) return;
      const bounds = graphGroup.node().getBBox();
      const scale = Math.max(
        0.2,
        Math.min(1, width / (bounds.width + 80), height / (bounds.height + 80)),
      );
      svg.call(
        zoom.transform,
        d3.zoomIdentity
          .translate(width / 2, height / 2)
          .scale(scale)
          .translate(-bounds.x - bounds.width / 2, -bounds.y - bounds.height / 2),
      );
    });
    observer.observe(svgRef.current);
    return () => {
      observer.disconnect();
      simulation.stop();
    };
  }, [activeTab, graph, graphView, site, layoutMode, nodeColor, onSelectNode]);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const graphNodes = simulationRef.current?.nodes() || [];
    const selected = graphNodes.find((node) => node.id === selectedNodeId);
    if (!selected) {
      svg.selectAll("g.node-group, line, .graph-link-count").style("opacity", 1);
      return;
    }
    const connectedIds = new Set([selected.id]);
    svg.selectAll("line").each((link) => {
      const sourceId = typeof link.source === "object" ? link.source.id : link.source;
      const targetId = typeof link.target === "object" ? link.target.id : link.target;
      if (sourceId === selected.id || targetId === selected.id) {
        connectedIds.add(sourceId);
        connectedIds.add(targetId);
      }
    });
    svg
      .selectAll("g.node-group")
      .style("opacity", (node) => (connectedIds.has(node.id) ? 1 : 0.14));
    svg
      .selectAll("line")
      .style("opacity", (link) =>
        (typeof link.source === "object" ? link.source.id : link.source) === selected.id ||
        (typeof link.target === "object" ? link.target.id : link.target) === selected.id
          ? 1
          : 0.08,
      );
    svg
      .selectAll(".graph-link-count")
      .style("opacity", (link) =>
        (typeof link.source === "object" ? link.source.id : link.source) === selected.id ||
        (typeof link.target === "object" ? link.target.id : link.target) === selected.id
          ? 1
          : 0.08,
      );
  }, [activeTab, graph, graphView, layoutMode, site, nodeColor, onSelectNode, selectedNodeId]);

  useEffect(() => {
    if (!svgRef.current || !graph) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll(".node-crawl-pulse").remove();
    if (currentUrl) {
      const normalizedUrl = currentUrl.replace(/\/$/, "");
      svg
        .select("g")
        .selectAll("g.node-group")
        .filter(
          (node) =>
            node &&
            (node.url?.replace(/\/$/, "") === normalizedUrl ||
              node.memberNodes?.some((member) => member.url?.replace(/\/$/, "") === normalizedUrl)),
        )
        .insert("circle", ":first-child")
        .attr("class", "node-crawl-pulse")
        .attr("r", 10);
    }
    svg.selectAll("g.node-group").each(function (nodeData) {
      if (!nodeData) return;
      const g = d3.select(this);
      g.selectAll(".node-llm-pulse").remove();
      if (needsLlmAnalysis(nodeData)) {
        g.insert("circle", ":first-child").attr("class", "node-llm-pulse").attr("r", 10);
      }
    });
  }, [currentUrl, graph]);

  // Retune the centering force in place when the gravity setting changes so
  // dragging the debug slider doesn't reset node positions/zoom.
  useEffect(() => {
    const simulation = simulationRef.current;
    if (!simulation) return;
    if (layoutMode !== "api-lanes") simulation.force("x")?.strength(gravity);
    simulation.force("y")?.strength(gravity);
    simulation.alpha(0.3).restart();
  }, [gravity, layoutMode]);

  useEffect(() => {
    if (!svgRef.current) return;
    d3.select(svgRef.current)
      .selectAll("g.node-group")
      .classed("sitemap-search-match", (node) => searchMatches?.has(node.id) || false);
  }, [searchMatches, activeTab, graph, graphView, layoutMode, site, nodeColor, onSelectNode]);

  return { svgRef };
}
