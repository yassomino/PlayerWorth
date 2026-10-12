import Link from "next/link";
import type { RankingResponse } from "@/lib/api/types";
import { formatMoney, fullMoney } from "@/lib/format";
import { ValueDelta } from "../player/ValueDelta";
import { PlayerAvatar } from "../player/PlayerAvatar";

export function RankingsTable({ data }: { data: RankingResponse }) {
  return (
    <table className="rankings-table">
      <caption className="sr-only">
        API-ranked model differences for {data.season}; predicted minus observed
        market value
      </caption>
      <thead>
        <tr>
          {[
            "Rank",
            "Player / primary club",
            "Position",
            "Observed value",
            "Model estimate",
            "Difference",
          ].map((label) => (
            <th key={label} scope="col">
              {label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.items.map((player) => (
          <tr key={player.player_id}>
            <td className="rankings-rank">
              <span className="sr-only">Rank </span>
              {String(player.rank).padStart(2, "0")}
            </td>
            <th scope="row" className="rankings-player">
              <Link
                href={`/players/${player.player_id}?${new URLSearchParams({ season: player.season })}`}
              >
                <PlayerAvatar name={player.player_name} />
                <span>
                  <strong>{player.player_name}</strong>
                  <small>{player.club ?? "Club unavailable"}</small>
                </span>
                <span className="rankings-arrow" aria-hidden="true">
                  ↗
                </span>
              </Link>
            </th>
            <td className="rankings-position">
              <span className="sr-only">Position </span>
              {player.position ?? "Unmapped"}
            </td>
            <td className="rankings-observed">
              <span className="rankings-mobile-label">Observed value</span>
              <strong title={fullMoney(player.observed_value_eur)}>
                {formatMoney(player.observed_value_eur)}
              </strong>
            </td>
            <td className="rankings-estimate">
              <span className="rankings-mobile-label">Model estimate</span>
              <strong title={fullMoney(player.predicted_value_eur)}>
                {formatMoney(player.predicted_value_eur)}
              </strong>
            </td>
            <td className="rankings-delta">
              <ValueDelta value={player.difference_eur} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
