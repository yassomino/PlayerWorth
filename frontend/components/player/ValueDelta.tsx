import { formatDifference, fullMoney } from "@/lib/format";
export function ValueDelta({
  value,
  comparison = "observed value",
}: {
  value: number | null;
  comparison?: string;
}) {
  if (value === null)
    return <p className="pp-unavailable">Difference unavailable</p>;
  const direction = value > 0 ? "above" : value < 0 ? "below" : "equal to";
  return (
    <div
      className={`pp-delta ${value < 0 ? "negative" : value > 0 ? "positive" : "neutral"}`}
    >
      <strong title={fullMoney(value)}>{formatDifference(value)}</strong>
      <span>
        {comparison === "observed value"
          ? "Model estimate"
          : "Simulated estimate"}{" "}
        {direction} {comparison}
      </span>
    </div>
  );
}
