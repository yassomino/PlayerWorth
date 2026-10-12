export function formatMoney(value: number, decimals = 1): string {
  const absolute = Math.abs(value);
  const [scale, suffix] =
    absolute >= 1e9
      ? [1e9, "B"]
      : absolute >= 1e6
        ? [1e6, "M"]
        : absolute >= 1e3
          ? [1e3, "K"]
          : [1, ""];
  return `${value < 0 ? "-" : ""}€${new Intl.NumberFormat("en-GB", { maximumFractionDigits: decimals }).format(absolute / scale)}${suffix}`;
}
export const formatDifference = (value: number) =>
  `${value > 0 ? "+" : ""}${formatMoney(value)}`;
export const fullMoney = (value: number) =>
  new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  }).format(value);

export const formatNumber = (value: number | null, decimals = 0) =>
  value === null
    ? "—"
    : new Intl.NumberFormat("en-GB", {
        maximumFractionDigits: decimals,
      }).format(value);
export const formatDate = (value: string) =>
  new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
