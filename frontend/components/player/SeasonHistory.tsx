import type { MarketValue, PlayerSeason } from "@/lib/api/types";
import { formatMoney, formatNumber } from "@/lib/format";
import { orderedSeasons, seasonObservation } from "@/lib/player";
export function SeasonHistory({
  seasons,
  values,
  selected,
  onSelect,
}: {
  seasons: PlayerSeason[];
  values: MarketValue[];
  selected: string;
  onSelect: (season: string) => void;
}) {
  return (
    <section className="pp-history" aria-labelledby="season-history-title">
      <div className="pp-section-title">
        <span className="eyebrow">THE LONGER VIEW</span>
        <h2 id="season-history-title">Season record</h2>
      </div>
      <div
        className="pp-table-wrap"
        tabIndex={0}
        role="region"
        aria-label="Scrollable season history"
      >
        <table>
          <caption className="sr-only">
            Stored Premier League seasons, newest first
          </caption>
          <thead>
            <tr>
              {[
                "Season",
                "Primary club",
                "Age",
                "Apps",
                "Minutes",
                "Goals",
                "Assists",
                "Observed value",
              ].map((label) => (
                <th key={label} scope="col">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {orderedSeasons(seasons).map((season) => {
              const observation = seasonObservation(season, values);
              return (
                <tr
                  key={season.season}
                  className={selected === season.season ? "selected" : ""}
                >
                  <th scope="row">
                    <button
                      type="button"
                      aria-pressed={selected === season.season}
                      onClick={() => onSelect(season.season)}
                    >
                      {season.season} <span aria-hidden="true">↗</span>
                    </button>
                  </th>
                  <td>{season.club ?? "Unavailable"}</td>
                  <td>{formatNumber(season.age)}</td>
                  <td>{season.appearances}</td>
                  <td>{formatNumber(season.minutes)}</td>
                  <td>{season.goals}</td>
                  <td>{season.assists}</td>
                  <td>
                    {observation
                      ? formatMoney(observation.value_eur)
                      : "Unavailable"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="pp-note">
        Observed value: earliest Transfermarkt record within 45 days on or after
        the final league match. No out-of-window substitute.
      </p>
    </section>
  );
}
