import { modelHistory } from "@/lib/model-history";

/** HTML bars keep every value readable to assistive technology without duplicating chart data. */
export function ImportanceChart() {
  const maximum = Math.max(...modelHistory.importance.map((row) => row.gain));
  return (
    <figure className="lab-importance" aria-labelledby="importance-caption">
      <figcaption id="importance-caption">
        Final-fit normalized average split gain · all 13 transformed features
      </figcaption>
      <ol>
        {modelHistory.importance.map((row) => (
          <li key={row.feature}>
            <span className="lab-feature-name">{row.feature}</span>
            <span className="lab-bar-track" aria-hidden="true">
              <span
                className={
                  row.feature.startsWith("position_")
                    ? "position-bar"
                    : "numeric-bar"
                }
                style={{ width: `${(row.gain / maximum) * 100}%` }}
              />
            </span>
            <strong>{row.gain.toFixed(6)}</strong>
          </li>
        ))}
      </ol>
      <p className="analytics-note">
        Bars share a zero baseline; numbers are normalized gain, not euros.
        Position indicators sum to {modelHistory.positionFamilyGain.toFixed(9)}.
      </p>
    </figure>
  );
}
