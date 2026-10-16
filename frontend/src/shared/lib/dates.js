export function parseDate(val) {
  if (!val) return new Date(val);
  if (val instanceof Date) return val;
  let s = String(val).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s) && !/[Zz]|[+-]\d{2}:?\d{2}$/.test(s)) {
    s = s.replace(" ", "T");
    if (!s.endsWith("Z")) {
      s += "Z";
    }
  }
  return new Date(s);
}

export function fmtDate(iso) {
  if (!iso) return "—";
  const date = parseDate(iso);
  if (Number.isNaN(date.getTime())) return String(iso);
  return date.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
}

// 24-hour HH:MM:SS, used by activity feeds and agent logs.
export function fmtTime(iso, fallback = "—") {
  if (!iso) return fallback;
  const date = parseDate(iso);
  if (Number.isNaN(date.getTime())) return fallback;
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
