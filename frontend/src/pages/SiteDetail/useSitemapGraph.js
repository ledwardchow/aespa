import { useCallback, useEffect, useRef } from "react";
import * as d3 from "d3";
import { truncUrl } from "../../lib/utilities";
import { scopeColor, userColor } from "./_helpers";

// Owns the imperative D3 lifecycle while TestRunDetail keeps the selected-node
// state and the page-detail actions that depend on it.
export function useSitemapGraph({
  graph,
  activeTab,
  graphView,
  credentials,
  currentUrl,
  onSelectNode
}) {
  const svgRef = useRef(null);
  const simulationRef = useRef(null);
  const previousStructureKeyRef = useRef("");
  const nodeColor = useCallback(node => {
    if (graphView === "user") return userColor(node, credentials);
    return scopeColor(node);
  }, [credentials, graphView]);

  useEffect(() => {
    if (!graph || !svgRef.current) return;
    const structureKey = `${activeTab}:${graphView}:${graph.nodes.length}:${graph.links.length}`;

    // Status-only updates retain the settled simulation and repaint in place.
    if (structureKey === previousStructureKeyRef.current && simulationRef.current) {
      const simulationNodes = simulationRef.current.nodes();
      graph.nodes.forEach(updatedNode => {
        const simulationNode = simulationNodes.find(node => node.id === updatedNode.id);
        if (simulationNode) Object.assign(simulationNode, updatedNode);
      });
      d3.select(svgRef.current).selectAll("circle.node-dot").filter(node => node && node.id != null).attr("fill", nodeColor);
      return;
    }

    previousStructureKeyRef.current = structureKey;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    const width = svgRef.current.clientWidth || 800;
    const height = svgRef.current.clientHeight || 500;
    const nodes = graph.nodes.map(node => ({ ...node }));
    const links = graph.links.map(link => ({ ...link }));
    const graphGroup = svg.append("g");
    const zoom = d3.zoom().scaleExtent([0.2, 4]).on("zoom", event => graphGroup.attr("transform", event.transform));
    svg.call(zoom);

    svg.append("defs").append("marker").attr("id", "arrow").attr("viewBox", "0 -4 8 8").attr("refX", 18).attr("refY", 0).attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto").append("path").attr("d", "M0,-4L8,0L0,4").attr("fill", "var(--border-2)");
    const link = graphGroup.append("g").selectAll("line").data(links).join("line").attr("stroke", "var(--border-2)").attr("stroke-width", 1.5).attr("marker-end", "url(#arrow)");
    const simulation = d3.forceSimulation(nodes).force("link", d3.forceLink(links).id(node => node.id).distance(110).strength(0.8)).force("charge", d3.forceManyBody().strength(-350)).force("center", d3.forceCenter(width / 2, height / 2)).force("x", d3.forceX(width / 2).strength(0.06)).force("y", d3.forceY(height / 2).strength(0.06)).force("collision", d3.forceCollide(22));
    const node = graphGroup.append("g").selectAll("g").data(nodes).join("g").attr("cursor", "pointer").call(d3.drag().on("start", (event, draggedNode) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      draggedNode.fx = draggedNode.x;
      draggedNode.fy = draggedNode.y;
    }).on("drag", (event, draggedNode) => {
      draggedNode.fx = event.x;
      draggedNode.fy = event.y;
    }).on("end", (event, draggedNode) => {
      if (!event.active) simulation.alphaTarget(0);
      draggedNode.fx = null;
      draggedNode.fy = null;
    })).on("click", (event, clickedNode) => {
      event.stopPropagation();
      onSelectNode(clickedNode);
    });

    node.append("circle").attr("class", "node-dot").attr("r", 10).attr("fill", nodeColor).attr("stroke", node => node.status === "failed" ? "#fbbf24" : "var(--bg)").attr("stroke-width", 2);
    const rootNode = nodes.find(node => node.depth === 0);
    let baseHost = null;
    try {
      if (rootNode) baseHost = new URL(rootNode.url).host;
    } catch {}
    node.append("text").attr("dy", 22).attr("text-anchor", "middle").attr("fill", "var(--muted)").attr("font-size", "10px").attr("pointer-events", "none").text(node => {
      try {
        const url = new URL(node.url);
        const label = url.host === baseHost ? url.pathname + url.search + url.hash || "/" : node.url;
        return label.length > 36 ? label.slice(0, 35) + "…" : label;
      } catch {
        return truncUrl(node.url, 36);
      }
    });
    node.append("title").text(node => node.url);
    svg.on("click", () => onSelectNode(null));
    simulation.on("tick", () => {
      link.attr("x1", node => node.source.x).attr("y1", node => node.source.y).attr("x2", node => node.target.x).attr("y2", node => node.target.y);
      node.attr("transform", node => `translate(${node.x},${node.y})`);
    });
    simulationRef.current = simulation;
    return () => simulation.stop();
  }, [activeTab, graph, graphView, nodeColor, onSelectNode]);

  useEffect(() => {
    if (!svgRef.current || !graph) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll(".node-crawl-pulse").remove();
    if (!currentUrl) return;
    const normalizedUrl = currentUrl.replace(/\/$/, "");
    svg.select("g").selectAll("g").filter(node => node && node.url && node.url.replace(/\/$/, "") === normalizedUrl).insert("circle", ":first-child").attr("class", "node-crawl-pulse").attr("r", 10);
  }, [currentUrl, graph]);

  return { svgRef };
}
