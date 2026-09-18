export function matchesSitemapSearch(node, term) {
  const query = term.trim().toLowerCase();
  if (!query) return false;
  return [node, ...(node.memberNodes || [])].some((item) =>
    [
      item.url,
      item.title,
      item.state_label,
      item.routePath,
      item.apiPath,
      item.apiMethod,
      item.isDiscoveryGroup ? "Direct scan discoveries" : "",
    ].some((value) => typeof value === "string" && value.toLowerCase().includes(query)),
  );
}
