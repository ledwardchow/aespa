export function fmtUsd(value) {
  if (value === null || value === undefined) return "—";
  const number = Number(value);
  return `$${number.toFixed(number >= 100 ? 0 : number >= 1 ? 2 : 4)}`;
}

export function fmtPercent(value) {
  if (value === null || value === undefined) return "—";
  return `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
}

export function fmtTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** Parse "3h 12m", "2d 4h" or "45m" into milliseconds. */
export function parseDuration(text) {
  const value = String(text || "")
    .trim()
    .toLowerCase();
  if (!value) return null;
  const pattern = /(\d+(?:\.\d+)?)\s*(days?|d|hours?|hrs?|h|minutes?|mins?|m)/g;
  const units = { d: 86_400_000, h: 3_600_000, m: 60_000 };
  let total = 0;
  let matched = "";
  for (const match of value.matchAll(pattern)) {
    total += Number(match[1]) * units[match[2][0]];
    matched += match[0];
  }
  if (!matched || matched.replace(/\s/g, "") !== value.replace(/\s/g, "")) return null;
  return total;
}
