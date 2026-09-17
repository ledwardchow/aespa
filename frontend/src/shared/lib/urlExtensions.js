export function parseExcludedExtensions(value) {
  return new Set(
    value
      .split(",")
      .map((part) => part.trim().toLowerCase())
      .filter(Boolean)
      .map((part) => (part.startsWith(".") ? part : `.${part}`)),
  );
}

export function extractUrlExtension(url) {
  try {
    const pathname = new URL(url).pathname || "";
    const slash = pathname.lastIndexOf("/");
    const segment = slash >= 0 ? pathname.slice(slash + 1) : pathname;
    const dot = segment.lastIndexOf(".");
    if (dot <= 0 || dot === segment.length - 1) return "";
    return segment.slice(dot).toLowerCase();
  } catch {
    return "";
  }
}

export function isApiGraphNode(node) {
  if (node?.state_kind === "api" || node?.isApiGroup) return true;
  const context = String(node?.context || "").trimStart();
  if (/^\[api endpoint\b/i.test(context)) return true;
  return /^API\s+(?:GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b/i.test(node?.title || "");
}

export function filterSitemapGraph(graph, excludedExtensions, hideApis = false) {
  if (!graph || (excludedExtensions.size === 0 && !hideApis)) return graph;

  const nodes = graph.nodes.filter(
    (node) =>
      !excludedExtensions.has(extractUrlExtension(node.url)) &&
      (!hideApis || !isApiGraphNode(node)),
  );
  const nodeIds = new Set(nodes.map((node) => node.id));
  const links = graph.links.filter((link) => {
    const source = typeof link.source === "object" ? link.source?.id : link.source;
    const target = typeof link.target === "object" ? link.target?.id : link.target;
    return nodeIds.has(source) && nodeIds.has(target);
  });

  return { ...graph, nodes, links };
}
