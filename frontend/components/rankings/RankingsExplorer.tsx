"use client";
import { useEffect, useState } from "react";
import {
  ApiError,
  getOvervaluedRankings,
  getUndervaluedRankings,
} from "@/lib/api/client";
import type { RankingResponse } from "@/lib/api/types";
import {
  rankingSelection,
  rankingSeasons,
  rankingsUrl,
  validRankingSelection,
  type RankingSelection,
} from "@/lib/rankings";
import { formatNumber } from "@/lib/format";
import { Skeleton } from "../ui/States";
import { RankingsTable } from "./RankingsTable";

function RankingResults({ selection }: { selection: RankingSelection }) {
  const [data, setData] = useState<RankingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const request =
      selection.direction === "above"
        ? getUndervaluedRankings
        : getOvervaluedRankings;
    request(20, selection.season, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setData(result);
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        setError(
          error instanceof ApiError && [404, 422].includes(error.status)
            ? "Rankings are unavailable for this season. Choose another stored season."
            : "Rankings are temporarily unavailable. The data service or model may be offline. Please try again.",
        );
      });
    return () => controller.abort();
  }, [selection.direction, selection.season, attempt]);
  if (error)
    return (
      <div className="analytics-empty" role="alert">
        <h2>Rankings unavailable</h2>
        <p>{error}</p>
        <button
          className="analytics-button"
          onClick={() => {
            setError(null);
            setAttempt((value) => value + 1);
          }}
        >
          Retry rankings
        </button>
      </div>
    );
  if (!data) return <Skeleton rows={6} />;
  return (
    <>
      <div className="rankings-summary" role="status">
        <p>
          <strong>{data.season}</strong> · {data.model_name} · v
          {data.model_version}
        </p>
        <p>
          Showing {data.items.length} · {formatNumber(data.eligible_rows)}{" "}
          eligible · {formatNumber(data.excluded_rows)} excluded before ranking
        </p>
      </div>
      <p className="analytics-note rankings-order">
        {selection.direction === "above"
          ? "Largest positive differences first."
          : "Most negative differences first."}{" "}
        Difference = model estimate − observed value. Up to 20 results, in API
        order.
      </p>
      {data.items.length ? (
        <RankingsTable data={data} />
      ) : (
        <div className="analytics-empty" role="status">
          <h2>No matching ranking rows</h2>
          <p>
            No eligible players have a model estimate {selection.direction} the
            observed value for this season. Try the other direction or another
            season.
          </p>
        </div>
      )}
    </>
  );
}

export function RankingsExplorer({
  initialSelection,
}: {
  initialSelection: RankingSelection;
}) {
  const [selection, setSelection] = useState(initialSelection);
  useEffect(() => {
    const onPop = () =>
      setSelection(
        rankingSelection(new URLSearchParams(window.location.search)),
      );
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  function choose(next: RankingSelection) {
    if (
      next.direction === selection.direction &&
      next.season === selection.season
    )
      return;
    setSelection(next);
    window.history.pushState(null, "", rankingsUrl(next));
  }
  return (
    <div className="container analytics-page rankings-page">
      <header className="analytics-hero rankings-hero">
        <div>
          <span className="eyebrow">
            MODEL RANKINGS / A DIFFERENT READING OF THE GAME
          </span>
          <h1>
            Where the
            <br />
            <span className="muted">estimates disagree.</span>
          </h1>
          <p>
            Model-estimated differences between PlayerWorth V1 and stored
            observed market values.
          </p>
        </div>
        <div className="rankings-formula" aria-hidden="true">
          <span>MODEL ESTIMATE</span>
          <b>−</b>
          <span>OBSERVED VALUE</span>
          <b>=</b>
          <strong>A DIFFERENT PERSPECTIVE</strong>
        </div>
      </header>
      <div className="rankings-controls">
        <div
          className="rankings-toggle"
          role="group"
          aria-label="Ranking direction"
        >
          {["above", "below"].map((direction) => (
            <button
              key={direction}
              type="button"
              aria-pressed={selection.direction === direction}
              onClick={() => choose({ ...selection, direction })}
            >
              <span aria-hidden="true">
                {direction === "above" ? "↗" : "↘"}
              </span>{" "}
              Model {direction === "above" ? "Above" : "Below"} Observed
            </button>
          ))}
        </div>
        <div className="rankings-season">
          <label htmlFor="rankings-season">Season</label>
          <select
            id="rankings-season"
            value={selection.season}
            onChange={(event) =>
              choose({ ...selection, season: event.target.value })
            }
          >
            {!rankingSeasons.includes(selection.season) && (
              <option value={selection.season}>Unavailable season</option>
            )}
            {rankingSeasons.map((season) => (
              <option key={season}>{season}</option>
            ))}
          </select>
        </div>
      </div>
      <aside className="rankings-disclaimer">
        <p>
          These rankings compare model estimates with stored observed market
          values. They are analytical model outputs, not objective player
          valuations.
        </p>
        <p>
          The final V1 model was fitted on all five stored seasons. These are
          descriptive outputs on known observations, not unseen-season
          evaluation. <a href="/models#temporal">Understand the evaluation ↗</a>
        </p>
      </aside>
      <section
        className="rankings-results"
        aria-label="Selected rankings"
        aria-live="polite"
      >
        {validRankingSelection(selection) ? (
          <RankingResults
            key={`${selection.season}-${selection.direction}`}
            selection={selection}
          />
        ) : (
          <div className="analytics-empty" role="alert">
            <h2>Unavailable ranking selection</h2>
            <p>
              Choose a stored season and an above/below direction. No substitute
              ranking has been loaded.
            </p>
            <button
              className="analytics-button"
              onClick={() =>
                choose({ season: rankingSeasons[0], direction: "above" })
              }
            >
              Show latest rankings
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
