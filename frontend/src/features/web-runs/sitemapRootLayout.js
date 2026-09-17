function canonicalUrl(value, base) {
  try {
    const url = new URL(value, base);
    url.pathname = url.pathname.replace(/\/+$/, "") || "/";
    return url.href;
  } catch {
    return null;
  }
}

export function markSiteEntries(nodes, site) {
  const ordered = [...nodes].sort(
    (a, b) => (a.depth ?? 0) - (b.depth ?? 0) || String(a.id).localeCompare(String(b.id)),
  );
  nodes.forEach((node) => {
    node.entryRole = undefined;
    node.isSiteEntry = false;
  });
  const entries = [
    [site?.base_url, "Landing page"],
    [site?.login_url, "Login page"],
    ...(site?.credentials || []).map((credential) => [credential.login_url, "Login page"]),
  ].filter(([url]) => url);
  for (const [url, role] of entries) {
    const canonical = canonicalUrl(url, site?.base_url);
    const match =
      canonical &&
      ordered.find(
        (node) =>
          !node.isApiGroup &&
          !node.isApiNode &&
          !node.isDiscoveryGroup &&
          (node.memberNodes || [node]).some(
            (member) => canonicalUrl(member.url, site?.base_url) === canonical,
          ),
      );
    if (match && !match.isSiteEntry) {
      match.entryRole = role;
      match.isSiteEntry = true;
    }
  }
}
