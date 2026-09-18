import { filterSitemapGraph, isApiGraphNode } from "../../shared/lib/urlExtensions.js";

const API_TITLE_RE = /^API\s+([A-Z]+)(?:\s+\d{3})?\b/i;
const UUID_SEGMENT_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const HEX_SEGMENT_RE = /^[0-9a-f]{16,}$/i;

const linkNodeId = (value) => (typeof value === "object" ? value?.id : value);

function isDynamicDiscoveryNode(node) {
  const members = node.memberNodes || [node];
  return members.some(
    (member) =>
      String(member?.title || "").startsWith("Dynamic ") ||
      String(member?.context || "").startsWith("Discovered during Dynamic Scan."),
  );
}

export function apiMethod(node) {
  return (
    String(node?.title || "")
      .match(API_TITLE_RE)?.[1]
      ?.toUpperCase() || "GET"
  );
}

function normalizeSegment(segment) {
  if (/^\d+$/.test(segment) || UUID_SEGMENT_RE.test(segment) || HEX_SEGMENT_RE.test(segment)) {
    return "{id}";
  }
  return segment;
}

function normalizeRouteSegments(segments, source) {
  const slots = [];
  const normalized = segments.map((segment, index) => {
    const value = normalizeSegment(segment);
    if (value === "{id}") slots.push({ source, index });
    return value;
  });
  return { normalized, slots };
}

function endpointIdentity(node) {
  try {
    const url = new URL(node.url);
    const route = normalizeRouteSegments(url.pathname.split("/"), "path");
    const path = route.normalized.join("/") || "/";
    return {
      key: `${apiMethod(node)} ${url.origin}${path}`,
      method: apiMethod(node),
      origin: url.origin,
      path,
      slots: route.slots,
    };
  } catch {
    return {
      key: `${apiMethod(node)} ${node.url}`,
      method: apiMethod(node),
      origin: "",
      path: node.url || "/",
      slots: [],
    };
  }
}

function pageRouteIdentity(node) {
  try {
    const url = new URL(node.url);
    const pathname = normalizeRouteSegments(url.pathname.split("/"), "path");
    let fragment = url.hash;
    let fragmentSlots = [];
    if (url.hash.startsWith("#/")) {
      const fragmentRoute = normalizeRouteSegments(url.hash.slice(1).split("/"), "fragment");
      fragment = `#${fragmentRoute.normalized.join("/")}`;
      fragmentSlots = fragmentRoute.slots;
    }
    const path = `${pathname.normalized.join("/") || "/"}${fragment}`;
    return {
      key: `${url.origin}${path}`,
      origin: url.origin,
      path,
      slots: [...pathname.slots, ...fragmentSlots],
    };
  } catch {
    return { key: node.url, origin: "", path: node.url || "/", slots: [] };
  }
}

function collectParameters(memberNodes, identity) {
  const query = new Map();
  const path = new Map();

  for (const node of memberNodes) {
    try {
      const url = new URL(node.url);
      for (const [name, value] of url.searchParams) {
        if (!query.has(name)) query.set(name, new Set());
        query.get(name).add(value);
      }
      const observed = {
        path: url.pathname.split("/"),
        fragment: url.hash.startsWith("#/") ? url.hash.slice(1).split("/") : [],
      };
      identity.slots.forEach((slot, position) => {
        const value = observed[slot.source]?.[slot.index];
        if (value == null) return;
        const name = identity.slots.length === 1 ? "id" : `id_${position + 1}`;
        if (!path.has(name)) path.set(name, new Set());
        path.get(name).add(value);
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

function groupedNodeBase(identity, memberNodes) {
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
    url: `${identity.origin}${identity.path}`,
    depth: Math.min(...memberNodes.map((node) => node.depth ?? 0)),
    status: failed ? "failed" : "crawled",
    analysis_status: analysisPending ? "pending" : "complete",
    in_scope: inScope,
    scan_status: memberNodes.some((node) => node.scan_status === "running") ? "running" : "pending",
    accessible_by: [...accessibleBy],
    accessible_anonymously: accessibleAnonymously,
    memberNodes,
    memberIds: memberNodes.map((node) => node.id),
    variants,
    variantCount: variants.length,
    parameters: collectParameters(memberNodes, identity),
  };
}

function groupedApiNode(identity, memberNodes) {
  return {
    ...groupedNodeBase(identity, memberNodes),
    id: `api-group:${identity.key}`,
    title: `${identity.method} ${identity.path}`,
    context: `[Grouped API endpoint] ${memberNodes.length} observed request variant${memberNodes.length === 1 ? "" : "s"}.`,
    isApiGroup: true,
    apiMethod: identity.method,
    apiPath: identity.path,
    apiOrigin: identity.origin,
    callers: [],
  };
}

function groupedPageNode(identity, memberNodes) {
  return {
    ...groupedNodeBase(identity, memberNodes),
    id: `page-group:${identity.key}`,
    title: identity.path,
    state_label: identity.path,
    state_kind: "url",
    context: `[Grouped page route] ${memberNodes.length} observed URL variants.`,
    isPageGroup: true,
    routePath: identity.path,
    routeOrigin: identity.origin,
    connections: [],
  };
}

function groupPageRoutes(pageNodes, pageDisplay) {
  if (pageDisplay !== "grouped") {
    return { nodes: pageNodes, nodeToGroup: new Map(), groups: [] };
  }

  const candidates = new Map();
  const individualNodes = [];
  for (const node of pageNodes) {
    if (node.state_kind === "interactive") {
      individualNodes.push(node);
      continue;
    }
    const identity = pageRouteIdentity(node);
    if (!candidates.has(identity.key)) candidates.set(identity.key, { identity, members: [] });
    candidates.get(identity.key).members.push(node);
  }

  const groups = [];
  const nodeToGroup = new Map();
  for (const { identity, members } of candidates.values()) {
    if (members.length < 2) {
      individualNodes.push(...members);
      continue;
    }
    const group = groupedPageNode(identity, members);
    groups.push(group);
    for (const member of members) nodeToGroup.set(member.id, group.id);
  }
  return { nodes: [...individualNodes, ...groups], nodeToGroup, groups };
}

export function buildSitemapDisplayGraph(
  graph,
  excludedExtensions,
  apiDisplay = "grouped",
  pageDisplay = "grouped",
) {
  if (!graph) return null;
  const extensionFiltered = filterSitemapGraph(graph, excludedExtensions, false);
  const apiNodes = extensionFiltered.nodes.filter(isApiGraphNode);
  const rawPageNodes = extensionFiltered.nodes.filter((node) => !isApiGraphNode(node));
  const pageResult = groupPageRoutes(rawPageNodes, pageDisplay);
  const nodeToGroup = new Map(pageResult.nodeToGroup);

  let apiDisplayNodes = [];
  let apiGroupNodes = [];
  if (apiDisplay === "grouped") {
    const groups = new Map();
    for (const node of apiNodes) {
      const identity = endpointIdentity(node);
      if (!groups.has(identity.key)) groups.set(identity.key, { identity, members: [] });
      groups.get(identity.key).members.push(node);
    }
    apiGroupNodes = [...groups.values()].map(({ identity, members }) =>
      groupedApiNode(identity, members),
    );
    apiDisplayNodes = apiGroupNodes;
    for (const group of apiGroupNodes) {
      for (const memberId of group.memberIds) nodeToGroup.set(memberId, group.id);
    }
  } else if (apiDisplay === "individual") {
    apiDisplayNodes = apiNodes.map((node) => ({ ...node, isApiNode: true }));
  }

  const nodes = [...pageResult.nodes, ...apiDisplayNodes];
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const pageNodeById = new Map(pageResult.nodes.map((node) => [node.id, node]));
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

  const connectedNodeIds = new Set();
  for (const link of linksByKey.values()) {
    connectedNodeIds.add(link.source);
    connectedNodeIds.add(link.target);
  }
  const directDiscoveries = nodes.filter(
    (node) => !connectedNodeIds.has(node.id) && isDynamicDiscoveryNode(node),
  );
  if (directDiscoveries.length > 0) {
    const discoveryHub = {
      id: "dynamic-discovery-hub",
      url: "Direct scan discoveries",
      title: "Direct scan discoveries",
      state_label: "Direct scan discoveries",
      state_kind: "discovery",
      depth: 0,
      status: "crawled",
      analysis_status: "complete",
      scan_status: "complete",
      in_scope: true,
      accessible_by: [],
      accessible_anonymously: false,
      context: "Routes observed by the Dynamic Scan without a recorded source page.",
      isDiscoveryGroup: true,
      discoveryCount: directDiscoveries.length,
    };
    nodes.push(discoveryHub);
    nodeById.set(discoveryHub.id, discoveryHub);
    for (const discovery of directDiscoveries) {
      linksByKey.set(`${discoveryHub.id}>${discovery.id}`, {
        source: discoveryHub.id,
        target: discovery.id,
        action_kind: "dynamic_discovery",
        count: 1,
      });
    }
  }

  for (const link of linksByKey.values()) {
    const target = nodeById.get(link.target);
    const source = pageNodeById.get(link.source);
    if (target?.isApiGroup && source) {
      target.callers.push({
        id: source.id,
        label: source.state_label || source.title || source.url,
        url: source.url,
        observationCount: link.count,
      });
    }
    for (const [group, direction, other] of [
      [nodeById.get(link.source), "Outgoing", nodeById.get(link.target)],
      [nodeById.get(link.target), "Incoming", nodeById.get(link.source)],
    ]) {
      if (!group?.isPageGroup || !other) continue;
      group.connections.push({
        id: `${direction}:${other.id}`,
        direction,
        label: other.state_label || other.title || other.url,
        count: link.count,
      });
    }
  }
  for (const node of apiGroupNodes) {
    node.callers.sort((left, right) => left.label.localeCompare(right.label));
  }

  const groupedPageVariantCount = pageResult.groups.reduce(
    (total, group) => total + group.variantCount,
    0,
  );
  return {
    ...extensionFiltered,
    nodes,
    links: [...linksByKey.values()],
    displayStats: {
      excludedCount: graph.nodes.length - extensionFiltered.nodes.length,
      apiNodeCount: apiNodes.length,
      apiGroupCount: apiGroupNodes.length,
      pageGroupCount: pageResult.groups.length,
      groupedPageVariantCount,
    },
  };
}
