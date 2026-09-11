export function truncUrl(url, maxLen = 40) {
  try {
    const u = new URL(url);
    const s = u.hostname + u.pathname + u.hash;
    return s.length > maxLen ? s.slice(0, maxLen - 1) + "…" : s;
  } catch {
    return url.slice(0, maxLen);
  }
}
