import { filterSitemapGraph, isApiGraphNode } from "../../shared/lib/urlExtensions.js";

const API_TITLE_RE = /^API\s+([A-Z]+)(?:\s+\d{3})?\b/i;
const UUID_SEGMENT_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const HEX_SEGMENT_RE = /^[0-9a-f]{16,}$/i;

const linkNodeId = (value) => (typeof value === "object" ? value?.id : value);

export function apiMethod(node) {
  return (
    String(node?.title || "")
      .match(API_TITLE_RE)?.[1]
      ?.toUpperCase() || "GET"
  );
}

function normalizeApiPath(pathname) {
  const segments = String(pathname || "/").split("/");
  return (
    segments
      .map((segment) => {
        if (
          /^\d+$/.test(segment) ||
          UUID_SEGMENT_RE.test(segment) ||
          HEX_SEGMENT_RE.test(segment)
        ) {
          return "{id}";
        }
        return segment;
      })
      .join("/") || "/"
  );
}

function endpointIdentity(node) {
  try {
    const url = new URL(node.url);
    const path = normalizeApiPath(url.pathname);
    return {
      key: `${apiMethod(node)} ${url.origin}${path}`,
      method: apiMethod(node),
      origin: url.origin,
      path,
    };
  } catch {
    return {
      key: `${apiMethod(node)} ${node.url}`,
      method: apiMethod(node),
      origin: "",
      path: node.url || "/",
    };
  }
}

function collectParameters(memberNodes, normalizedPath) {
  const query = new Map();
  const path = new Map();
  const normalizedSegments = normalizedPath.split("/");
  const dynamicIndexes = normalizedSegments.flatMap((segment, index) =>
    segment === "{id}" ? [index] : [],
  );

  for (const node of memberNodes) {
    try {
      const url = new URL(node.url);
      for (const [name, value] of url.searchParams) {
        if (!query.has(name)) query.set(name, new Set());
        query.get(name).add(value);
      }
      const observedSegments = url.pathname.split("/");
      normalizedSegments.forEach((segment, index) => {
        if (segment !== "{id}" || observedSegments[index] == null) return;
        const position = dynamicIndexes.indexOf(index);
        const name = dynamicIndexes.length === 1 ? "id" : `id_${position + 1}`;
        if (!path.has(name)) path.set(name, new Set());
        path.get(name).add(observedSegments[index]);
      });
    } catch {}
  }

  const serialize = (entries, location) =>
    [...entries].map(([name, values]) => ({
      name,
      location,
      values: [...values].sort(),
    }));
  return [...serialize(path, "Path"), ...serialize(query, "Query")];
}

function groupedApiNode(identity, memberNodes) {
  const accessibleBy = new Set();
  let accessibleAnonymously = false;
  let inScope = false;
  let analysisPending = false;
  let failed = false;
  for (const node of memberNodes) {
    for (const credentialId of node.accessible_by || []) accessibleBy.add(credentialId);
    accessibleAnonymously ||= Boolean(node.accessible_anonymously);
    inScope ||= node.in_scope !== false;
    analysisPending ||= node.analysis_status === "pending";
    failed ||= node.status === "failed";
  }

  const variants = [...new Set(memberNodes.map((node) => node.url))].sort();
  return {
    id: `api-group:${identity.key}`,
    url: `${identity.origin}${identity.path}`,
    title: `${identity.method} ${identity.path}`,
    depth: Math.min(...memberNodes.map((node) => node.depth ?? 0)),
    status: failed ? "failed" : "crawled",
    context: `[Grouped API endpoint] ${memberNodes.length} observed request variant${memberNodes.length === 1 ? "" : "s"}.`,
    analysis_status: analysisPending ? "pending" : "complete",
    in_scope: inScope,
    scan_status: memberNodes.some((node) => node.scan_status === "running") ? "running" : "pending",
    accessible_by: [...accessibleBy],
    accessible_anonymously: accessibleAnonymously,
    isApiGroup: true,
    apiMethod: identity.method,
    apiPath: identity.path,
    apiOrigin: identity.origin,
    memberNodes,
    memberIds: memberNodes.map((node) => node.id),
    variants,
    variantCount: variants.length,
    parameters: collectParameters(memberNodes, identity.path),
    callers: [],
  };
}

export function buildSitemapDisplayGraph(graph, excludedExtensions, apiDisplay = "grouped") {
  if (!graph) return null;
  const extensionFiltered = filterSitemapGraph(graph, excludedExtensions, false);
  const apiNodes = extensionFiltered.nodes.filter(isApiGraphNode);

  if (apiDisplay === "individual") {
    return {
      ...extensionFiltered,
      displayStats: {
        excludedCount: graph.nodes.length - extensionFiltered.nodes.length,
        apiNodeCount: apiNodes.length,
        apiGroupCount: apiNodes.length,
      },
    };
  }
  if (apiDisplay === "hidden") {
    const hidden = filterSitemapGraph(extensionFiltered, new Set(), true);
    return {
      ...hidden,
      displayStats: {
        excludedCount: graph.nodes.length - extensionFiltered.nodes.length,
        apiNodeCount: apiNodes.length,
        apiGroupCount: 0,
      },
    };
  }

  const groups = new Map();
  const nodeToGroup = new Map();
  for (const node of apiNodes) {
    const identity = endpointIdentity(node);
    if (!groups.has(identity.key)) groups.set(identity.key, { identity, members: [] });
    groups.get(identity.key).members.push(node);
    nodeToGroup.set(node.id, `api-group:${identity.key}`);
  }

  const pageNodes = extensionFiltered.nodes.filter((node) => !isApiGraphNode(node));
  const apiGroupNodes = [...groups.values()].map(({ identity, members }) =>
    groupedApiNode(identity, members),
  );
  const nodes = [...pageNodes, ...apiGroupNodes];
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const pageNodeById = new Map(pageNodes.map((node) => [node.id, node]));
  const linksByKey = new Map();

  for (const rawLink of extensionFiltered.links) {
    const rawSource = linkNodeId(rawLink.source);
    const rawTarget = linkNodeId(rawLink.target);
    const source = nodeToGroup.get(rawSource) || rawSource;
    const target = nodeToGroup.get(rawTarget) || rawTarget;
    if (source === target || !nodeById.has(source) || !nodeById.has(target)) continue;
    const key = `${source}>${target}`;
    const existing = linksByKey.get(key);
    if (existing) {
      existing.count += 1;
      continue;
    }
    linksByKey.set(key, { ...rawLink, source, target, count: 1 });
  }

  for (const link of linksByKey.values()) {
    const target = nodeById.get(link.target);
    const source = pageNodeById.get(link.source);
    if (!target?.isApiGroup || !source) continue;
    target.callers.push({
      id: source.id,
      label: source.state_label || source.title || source.url,
      url: source.url,
      observationCount: link.count,
    });
  }
  for (const node of apiGroupNodes) {
    node.callers.sort((left, right) => left.label.localeCompare(right.label));
  }

  return {
    ...extensionFiltered,
    nodes,
    links: [...linksByKey.values()],
    displayStats: {
      excludedCount: graph.nodes.length - extensionFiltered.nodes.length,
      apiNodeCount: apiNodes.length,
      apiGroupCount: apiGroupNodes.length,
    },
  };
}
