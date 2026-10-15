const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

// One money format for the whole UI: two decimals with thousands separators,
// and extra precision only for sub-cent amounts so tiny per-call costs are not
// shown as $0.00.
export function fmtUsd(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  if (number !== 0 && Math.abs(number) < 0.01) return `$${number.toFixed(4)}`;
  return usd.format(number);
}
