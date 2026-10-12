import type { PlayerSeason } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
export function SeasonStats({ season }: { season: PlayerSeason }) {
  return (
    <section className="pp-stats" aria-labelledby="season-stats-title">
      <div className="pp-section-title">
        <span className="eyebrow">THE SEASON IN NUMBERS</span>
        <h2 id="season-stats-title">Performance, on the pitch.</h2>
      </div>
      <dl className="pp-stat-grid">
        {(
          [
            ["Appearances", season.appearances],
            ["Minutes", season.minutes],
            ["Goals", season.goals],
            ["Assists", season.assists],
          ] as const
        ).map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{formatNumber(value)}</dd>
          </div>
        ))}
      </dl>
      <dl className="pp-secondary-stats">
        {(
          [
            ["Goals / 90", formatNumber(season.goals_per_90, 2)],
            ["Assists / 90", formatNumber(season.assists_per_90, 2)],
            [
              "Goal contributions / 90",
              formatNumber(season.goal_contributions_per_90, 2),
            ],
            [
              "Yellow / red cards",
              `${season.yellow_cards} / ${season.red_cards}`,
            ],
            ["Clubs in season", String(season.clubs_in_season)],
          ] as const
        ).map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="pp-note">
        Season totals include all Premier League clubs played for. Per-90 rates
        and cards are descriptive statistics, not V1 model inputs.
      </p>
    </section>
  );
}
