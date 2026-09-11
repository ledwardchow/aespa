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
  return iso
    ? parseDate(iso).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })
    : "—";
}
