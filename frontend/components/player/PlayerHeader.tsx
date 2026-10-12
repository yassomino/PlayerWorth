import Link from "next/link";
import type { PlayerDetail, PlayerSeason } from "@/lib/api/types";
import { PlayerAvatar } from "./PlayerAvatar";
export function PlayerHeader({
  player,
  season,
}: {
  player: PlayerDetail["player"];
  season?: PlayerSeason;
}) {
  return (
    <header className="pp-header">
      <Link href="/#player-search" className="text-link">
        ← All players
      </Link>
      <div className="pp-header-main">
        <div className="pp-portrait">
          <PlayerAvatar
            name={player.name}
            position={season?.position ?? player.position}
            size="hero"
          />
          <span className="sr-only">
            {season?.position ?? player.position ?? "POSITION UNMAPPED"}
          </span>
        </div>
        <div className="pp-identity">
          <span className="eyebrow">PREMIER LEAGUE / PLAYER DOSSIER</span>
          <h1>{player.name}</h1>
          <p>
            {season?.club ?? "Club unavailable"} <span>·</span>{" "}
            {season?.season ?? "No season selected"}
          </p>
          <div className="pp-meta">
            <span>Age {season?.age ?? "unavailable"} at season end</span>
            {player.nationality && <span>{player.nationality}</span>}
            <span>Primary club for stored season</span>
          </div>
        </div>
        <a className="pp-simulator-link" href="#simulator">
          Explore a different scenario <span>↘</span>
        </a>
      </div>
    </header>
  );
}
