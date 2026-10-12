/** Stored V1 cohort, verified in docs/MODEL_CARD_V1.md. No season discovery endpoint exists. */
export const rankingSeasons = [
  "2025/26",
  "2024/25",
  "2023/24",
  "2022/23",
  "2021/22",
];
export interface RankingSelection {
  season: string;
  direction: string;
}
export function rankingSelection(query: URLSearchParams): RankingSelection {
  return {
    season:
      query.getAll("season").length > 1
        ? "invalid"
        : (query.get("season") ?? rankingSeasons[0]),
    direction:
      query.getAll("direction").length > 1
        ? "invalid"
        : (query.get("direction") ?? "above"),
  };
}
export function validRankingSelection(selection: RankingSelection) {
  return (
    rankingSeasons.includes(selection.season) &&
    ["above", "below"].includes(selection.direction)
  );
}
export function rankingsUrl(selection: RankingSelection) {
  return `/rankings?${new URLSearchParams({ season: selection.season, direction: selection.direction })}`;
}
