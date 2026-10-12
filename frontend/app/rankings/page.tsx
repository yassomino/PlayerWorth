import { RankingsExplorer } from "@/components/rankings/RankingsExplorer";
import { rankingSelection } from "@/lib/rankings";
import "@/components/ui/analytics.css";
export const metadata = {
  title: {
    absolute: "PlayerWorth Model Rankings — Estimated vs Observed Values",
  },
  description:
    "Explore descriptive differences between PlayerWorth model estimates and stored Premier League market values.",
};
export default async function Rankings({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const query = new URLSearchParams();
  for (const key of ["season", "direction"]) {
    const value = params[key];
    for (const item of Array.isArray(value)
      ? value
      : value === undefined
        ? []
        : [value])
      query.append(key, item);
  }
  return <RankingsExplorer initialSelection={rankingSelection(query)} />;
}
