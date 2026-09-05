export const DEFAULT_SITEMAP_GRAVITY = 0.06;

export const SITEMAP_GRAVITY_KEY = "aespa_sitemap_gravity";

export function getSitemapGravity() {
  try {
    const raw = localStorage.getItem(SITEMAP_GRAVITY_KEY);
    const val = raw === null ? NaN : parseFloat(raw);
    return Number.isFinite(val) ? Math.min(Math.max(val, 0), 0.2) : DEFAULT_SITEMAP_GRAVITY;
  } catch {
    return DEFAULT_SITEMAP_GRAVITY;
  }
}

export function setSitemapGravity(value) {
  try {
    localStorage.setItem(SITEMAP_GRAVITY_KEY, String(value));
  } catch {}
}
