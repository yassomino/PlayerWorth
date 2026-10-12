"use client";
import { useEffect, useMemo, useState } from "react";
import type { PlayerDetail } from "@/lib/api/types";
import { orderedSeasons } from "@/lib/player";
import { PlayerHeader } from "./PlayerHeader";
import { SeasonStats } from "./SeasonStats";
import { ModelInputsPanel } from "./ModelInputs";
import { SeasonEstimate } from "./SeasonEstimate";
import { ValuationHistory } from "./ValuationHistory";
import { SeasonHistory } from "./SeasonHistory";

export function PlayerProfile({
  data,
  initialSeason,
}: {
  data: PlayerDetail;
  initialSeason?: string;
}) {
  const seasons = useMemo(() => orderedSeasons(data.seasons), [data.seasons]);
  const [selected, setSelected] = useState(
    initialSeason ?? seasons[0]?.season ?? "",
  );
  const season = seasons.find((row) => row.season === selected);
  useEffect(() => {
    const onPop = () =>
      setSelected(
        new URLSearchParams(window.location.search).get("season") ??
          seasons[0]?.season ??
          "",
      );
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [seasons]);
  function choose(value: string) {
    setSelected(value);
    const url = new URL(window.location.href);
    url.searchParams.set("season", value);
    window.history.pushState(null, "", url);
  }
  return (
    <div className="container player-profile">
      <PlayerHeader player={data.player} season={season} />
      <div className="pp-season-bar">
        <div>
          <span className="eyebrow">SEASON EXPLORER</span>
          <p>One season. A complete picture.</p>
        </div>
        {seasons.length > 0 && (
          <div className="pp-season-select">
            <label htmlFor="profile-season">Selected season</label>
            <select
              id="profile-season"
              value={selected}
              onChange={(event) => choose(event.target.value)}
            >
              {!season && <option value={selected}>Unavailable season</option>}
              {seasons.map((row) => (
                <option key={row.season}>{row.season}</option>
              ))}
            </select>
          </div>
        )}
      </div>
      {season ? (
        <SeasonEstimate
          key={`${data.player.id}-${selected}`}
          id={data.player.id}
          season={season}
        >
          <div className="pp-performance-grid">
            <SeasonStats season={season} />
            <ModelInputsPanel season={season} />
          </div>
          <ValuationHistory values={data.market_values} />
        </SeasonEstimate>
      ) : (
        <section className="pp-empty" role="status">
          <h2>
            {seasons.length
              ? "Season not found"
              : "No stored seasons available"}
          </h2>
          <p>
            {seasons.length
              ? "Choose one of this player’s stored seasons above."
              : "There are no stored Premier League statistics for this player."}
          </p>
        </section>
      )}
      <SeasonHistory
        seasons={seasons}
        values={data.market_values}
        selected={selected}
        onSelect={choose}
      />
    </div>
  );
}
