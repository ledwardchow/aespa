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
