"use client";
import { useEffect, useState } from "react";
import { getPlayerPrediction } from "@/lib/api/client";
import type { PlayerPrediction, PlayerSeason } from "@/lib/api/types";
import { formatDate, formatMoney, fullMoney } from "@/lib/format";
import { Skeleton } from "../ui/States";
import { TransferSimulator } from "../simulator/TransferSimulator";
import { ValueDelta } from "./ValueDelta";

export function SeasonEstimate({
  id,
  season,
  children,
}: {
  id: number;
  season: PlayerSeason;
  children: React.ReactNode;
}) {
  const [prediction, setPrediction] = useState<PlayerPrediction | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    getPlayerPrediction(id, season.season, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setPrediction(result);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [id, season.season, attempt]);
  return (
    <>
      <section className="pp-value-hero" aria-label="Selected season valuation">
        <div className="pp-value-main">
          <span className="eyebrow">
            MODEL-ESTIMATED VALUE / {season.season}
          </span>
          {error ? (
            <div className="pp-local-error" role="alert">
              <h2>Estimate temporarily unavailable.</h2>
              <p>Your player profile and history are still available.</p>
              <button
                className="pp-reset"
                onClick={() => {
                  setError(false);
                  setAttempt((x) => x + 1);
                }}
              >
                Retry estimate
              </button>
            </div>
          ) : prediction ? (
            <>
              <strong
                className="pp-big-value"
                title={fullMoney(prediction.predicted_value_eur)}
                data-testid="model-estimate"
              >
                {formatMoney(prediction.predicted_value_eur)}
              </strong>
              <p className="pp-note">
                {prediction.model_name} · v{prediction.model_version} · Raw
                model output, not a true transfer value
              </p>
            </>
          ) : (
            <Skeleton rows={2} />
          )}
        </div>
        <div className="pp-observed">
          <span className="eyebrow">OBSERVED MARKET VALUE</span>
          {prediction ? (
            <>
              <strong
                title={
                  prediction.observed_value_eur === null
                    ? undefined
                    : fullMoney(prediction.observed_value_eur)
                }
              >
                {prediction.observed_value_eur === null
                  ? "Unavailable"
                  : formatMoney(prediction.observed_value_eur)}
              </strong>
              {prediction.observed_value_eur === null && (
                <p className="pp-note">Observed value unavailable</p>
              )}
              <ValueDelta value={prediction.difference_eur} />
            </>
          ) : (
            <p className="pp-note">
              {error
                ? "Valuation comparison unavailable"
                : "Loading valuation…"}
            </p>
          )}
          <p className="pp-note">
            Season ended {formatDate(season.season_end_date)}
          </p>
        </div>
      </section>
      {children}
      {prediction ? (
        <TransferSimulator
          key={`${season.season}-${prediction.model_version}`}
          baseline={prediction}
        />
      ) : (
        <section className="pp-simulator" id="simulator">
          <h2>Transfer Simulator</h2>
          {error ? (
            <p className="pp-note">
              Simulation requires an available season estimate. Retry above;
              your stored statistics remain unchanged.
            </p>
          ) : (
            <Skeleton rows={3} />
          )}
        </section>
      )}
    </>
  );
}
