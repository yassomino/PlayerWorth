import type { PlayerSeason } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
export function ModelInputsPanel({ season }: { season: PlayerSeason }) {
  return (
    <aside className="pp-input-panel" aria-labelledby="model-inputs-title">
      <span className="eyebrow">THE MODEL’S VIEW</span>
      <h2 id="model-inputs-title">Five inputs. One estimate.</h2>
      <dl>
        {(
          [
            ["Age", formatNumber(season.age)],
            ["Minutes", formatNumber(season.minutes)],
            ["Goals", formatNumber(season.goals)],
            ["Assists", formatNumber(season.assists)],
            ["Position", season.position ?? "Unmapped / unknown"],
          ] as const
        ).map(([name, value]) => (
          <div key={name}>
            <dt>{name}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="pp-note">
        Exactly what PlayerWorth V1 sees. Position is snapshot metadata, not
        independently verified historical position.
      </p>
    </aside>
  );
}
