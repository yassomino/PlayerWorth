import Link from "next/link";
import {
  getOvervaluedRankings,
  getUndervaluedRankings,
} from "@/lib/api/client";
import type { RankingResponse } from "@/lib/api/types";
import { formatDifference, formatMoney, fullMoney } from "@/lib/format";
import { PlayerAvatar } from "../player/PlayerAvatar";
import { Unavailable } from "../ui/States";
export function RankingCard({
  data,
  direction,
}: {
  data: RankingResponse;
  direction: "higher" | "lower";
}) {
  return (
    <div className={`ranking-card ${direction}`}>
      <div className="ranking-heading">
        <h3>
          <span aria-hidden="true">{direction === "higher" ? "↗" : "↘"}</span>{" "}
          Model {direction} than observed
        </h3>
        <span className="season-tag">{data.season}</span>
      </div>
      {data.items.length === 0 ? (
        <Unavailable>Ranking data isn&apos;t available right now.</Unavailable>
      ) : (
        <>
          <div className="ranking-columns">
            <span>PLAYER / CLUB</span>
            <span>MODEL / OBSERVED</span>
            <span>DIFFERENCE</span>
          </div>
          <ol>
            {data.items.map((player) => (
              <li key={player.player_id}>
                <Link
                  href={`/players/${player.player_id}`}
                  className="ranking-row"
                >
                  <div className="rank-player">
                    <PlayerAvatar name={player.player_name} />
                    <div>
                      <strong>{player.player_name}</strong>
                      <span>
                        {player.club ?? "Club unavailable"}{" "}
                        <b>· {player.position ?? "—"}</b>
                      </span>
                    </div>
                  </div>
                  <div className="rank-values">
                    <strong title={fullMoney(player.predicted_value_eur)}>
                      {formatMoney(player.predicted_value_eur)}
                    </strong>
                    <span title={fullMoney(player.observed_value_eur)}>
                      {formatMoney(player.observed_value_eur)}
                    </span>
                  </div>
                  <strong
                    className="difference"
                    title={fullMoney(player.difference_eur)}
                  >
                    {formatDifference(player.difference_eur)}
                  </strong>
                </Link>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
export async function RankingsPreview({
  direction,
}: {
  direction: "higher" | "lower";
}) {
  const data = await (
    direction === "higher"
      ? getUndervaluedRankings(3)
      : getOvervaluedRankings(3)
  ).catch(() => null);
  return data ? (
    <RankingCard direction={direction} data={data} />
  ) : (
    <div className="ranking-card">
      <h3>Model {direction} than observed</h3>
      <Unavailable>Ranking data isn&apos;t available right now.</Unavailable>
    </div>
  );
}
export function RankingDisclaimer() {
  return (
    <p className="ranking-disclaimer">
      Model-estimated differences are analytical outputs, not objective transfer
      valuations. These estimates describe stored training observations.
    </p>
  );
}
