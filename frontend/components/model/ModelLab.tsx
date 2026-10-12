import Link from "next/link";
import type { ModelResponse, RegisteredModel } from "@/lib/api/types";
import { modelHistory } from "@/lib/model-history";
import { formatMoney, fullMoney, formatNumber } from "@/lib/format";
import { ImportanceChart } from "./ImportanceChart";

const limitations = [
  [
    "Five inputs, many omissions",
    "Age, minutes, goals, assists and position only. No contract length, injuries, club strength, nationality/homegrown context, international performance or advanced xG/event data.",
  ],
  [
    "A snapshot of position",
    "Position metadata is snapshot-based, not independently verified for each historical season. Roles change; one category cannot capture every role.",
  ],
  [
    "Large misses still happen",
    "Superstar extrapolation remains difficult and individual errors can be large. Market value reflects many factors outside match statistics.",
  ],
  [
    "Premier League only",
    "Evidence covers stored Premier League observations. It does not establish performance in other leagues or guarantee future-season results.",
  ],
];

export function ModelLab({
  current,
  registered,
}: {
  current: ModelResponse | null;
  registered: RegisteredModel[] | null;
}) {
  const { experiments, folds, pooled, per90Pooled } = modelHistory;
  return (
    <div className="container analytics-page model-lab">
      <header className="analytics-hero">
        <div>
          <span className="eyebrow">
            MODEL LAB / THE THINKING BEHIND THE NUMBER
          </span>
          <h1>
            Built through
            <br />
            <span className="muted">better questions.</span>
          </h1>
          <p>
            From linear regression to PlayerWorth V1. What improved prediction
            quality, what failed, and how we checked the results.
          </p>
        </div>
        <aside className="lab-current" aria-label="Current registered model">
          <span className="eyebrow">LIVE MODEL REGISTRY</span>
          {current ? (
            <>
              <h2>{current.model_name}</h2>
              <p>
                v{current.model_version} · {current.model_type}
              </p>
              <p>{current.feature_list.join(" / ")}</p>
              <dl>
                <div>
                  <dt>Temporal OOF MAE</dt>
                  <dd
                    title={
                      current.mae === null ? undefined : fullMoney(current.mae)
                    }
                  >
                    {current.mae === null
                      ? "Unavailable"
                      : formatMoney(current.mae, 2)}
                  </dd>
                </div>
                <div>
                  <dt>Temporal OOF R²</dt>
                  <dd>{current.r2?.toFixed(6) ?? "Unavailable"}</dd>
                </div>
              </dl>
              <p>
                {formatNumber(current.training_row_count)} rows in the final fit
                · {formatNumber(current.evaluation_row_count)} earlier OOF
                predictions.
              </p>
              <p className="analytics-note">{current.evaluation_method}</p>
            </>
          ) : (
            <p role="status">
              Current model temporarily unavailable. The frozen experiment
              history below is still available.
            </p>
          )}
          {registered === null ? (
            <p className="analytics-note">Registry list unavailable.</p>
          ) : (
            <p className="analytics-note">
              {registered.length} registered model version
              {registered.length === 1 ? "" : "s"}. Historical experiments below
              are research records, not additional registered API models.
            </p>
          )}
        </aside>
      </header>
      <nav className="analytics-jump" aria-label="Model Lab sections">
        <a href="#evolution">01 / Evolution</a>
        <a href="#comparison">02 / Comparison</a>
        <a href="#temporal">03 / Temporal checks</a>
        <a href="#importance">04 / Inside V1</a>
      </nav>
      <section
        className="analytics-section"
        id="evolution"
        aria-labelledby="evolution-title"
      >
        <div className="analytics-section-heading">
          <div>
            <span className="eyebrow">01 / MODEL EVOLUTION</span>
            <h2 id="evolution-title">Every step had to earn its place.</h2>
          </div>
          <p>More complexity is useful only when the evidence supports it.</p>
        </div>
        <ol className="lab-evolution">
          {experiments.map((item, i) => (
            <li key={item.id}>
              <span className="lab-step">0{i + 1}</span>
              <h3>{item.name}</h3>
              <strong>
                {formatMoney(item.mae, 2)} <small>MAE</small>
              </strong>
              <p>{item.lesson}</p>
              <span className="analytics-note">2025/26 holdout</span>
            </li>
          ))}
          <li>
            <span className="lab-step">06</span>
            <h3>Final temporal validation</h3>
            <strong>
              4 <small>forward-season folds</small>
            </strong>
            <p>
              Check a feature across multiple seasons, not just one repeatedly
              inspected holdout.
            </p>
            <span className="analytics-note">Pooled OOF evaluation</span>
          </li>
        </ol>
      </section>
      <section
        className="analytics-section"
        id="comparison"
        aria-labelledby="comparison-title"
      >
        <span className="eyebrow">02 / THE EARLY EXPERIMENTS</span>
        <h2 id="comparison-title">
          Exploratory 2025/26 held-out-season comparison
        </h2>
        <p className="analytics-intro">
          All five use 2,090 training observations from 2021/22–2024/25 and the
          same 504 held-out observations. Selection procedures differ, and
          repeated inspection makes this exploratory—not an untouched final test
          leaderboard.
        </p>
        <div
          className="analytics-table-wrap"
          role="region"
          aria-label="Exploratory model comparison"
          tabIndex={0}
        >
          <table className="analytics-table">
            <caption className="sr-only">
              Exploratory 2025/26 metrics in EUR; lower MAE and RMSE are better
            </caption>
            <thead>
              <tr>
                {[
                  "Model",
                  "Features",
                  "MAE ↓",
                  "RMSE ↓",
                  "R² ↑",
                  "Outcome",
                ].map((label) => (
                  <th scope="col" key={label}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {experiments.map((item) => (
                <tr
                  key={item.id}
                  className={item.features === 5 ? "lab-preferred" : ""}
                >
                  <th scope="row">{item.name}</th>
                  <td>
                    {item.features === 4 ? "4 numerical" : "4 + position"}
                  </td>
                  <td>{fullMoney(item.mae)}</td>
                  <td>{fullMoney(item.rmse)}</td>
                  <td>{item.r2.toFixed(12)}</td>
                  <td>{item.outcome}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="lab-explainers">
          <article>
            <h3>MAE</h3>
            <p>
              Average absolute prediction error. Lower means a smaller average
              miss in euros.
            </p>
          </article>
          <article>
            <h3>RMSE</h3>
            <p>
              Root mean squared error. Penalizes large misses more heavily than
              MAE.
            </p>
          </article>
          <article>
            <h3>R²</h3>
            <p>
              Fraction of target variance explained relative to a constant
              target-mean baseline. It can be negative and is not an accuracy
              percentage.
            </p>
          </article>
        </div>
      </section>
      <section
        className="analytics-section"
        id="temporal"
        aria-labelledby="temporal-title"
      >
        <span className="eyebrow">03 / PAST SEASONS → THE NEXT SEASON</span>
        <h2 id="temporal-title">Move the clock forward.</h2>
        <p className="analytics-intro">
          Can historical seasons estimate a future season? Each expanding-window
          fold fits fresh preprocessing and a fresh model on earlier seasons,
          then predicts the next one.
        </p>
        <div className="lab-folds">
          {folds.map((fold) => (
            <article key={fold.fold}>
              <span className="eyebrow">FOLD {fold.fold}</span>
              <div className="lab-fold-track">
                {["2021/22", "2022/23", "2023/24", "2024/25", "2025/26"].map(
                  (season) => (
                    <span
                      key={season}
                      className={
                        fold.train.includes(season)
                          ? "training"
                          : fold.test === season
                            ? "testing"
                            : "unused"
                      }
                    >
                      {season}
                      <small>
                        {fold.train.includes(season)
                          ? "Train"
                          : fold.test === season
                            ? "Test"
                            : "—"}
                      </small>
                    </span>
                  ),
                )}
              </div>
              <p>
                {formatNumber(fold.trainRows)} training rows →{" "}
                {formatNumber(fold.testRows)} test rows
              </p>
            </article>
          ))}
        </div>
        <div className="lab-pooled">
          <div>
            <span className="eyebrow">
              ACCEPTED EVIDENCE / FROZEN POSITION MODEL
            </span>
            <h3>Temporal pooled out-of-fold evaluation</h3>
            <p>
              {formatNumber(pooled.rows)} predictions across 2022/23–2025/26.
              Recalculated from pooled errors, not averaged fold scores.
            </p>
          </div>
          <dl className="lab-metrics">
            {[
              ["MAE", fullMoney(pooled.mae)],
              ["RMSE", fullMoney(pooled.rmse)],
              ["R²", pooled.r2.toFixed(12)],
              [
                "Median absolute error",
                fullMoney(pooled.median_absolute_error_eur),
              ],
            ].map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <p className="analytics-note">
          A different protocol and cohort from the comparison above. These are
          earlier fold-model results, not test scores for the final model fitted
          on all five seasons. Frozen settings were originally selected using
          2024/25: this retrospective check is not fully nested historical model
          selection. Folds overlap, players recur, and four wins are not a
          significance test.
        </p>
        <div className="lab-decisions">
          <article>
            <span className="eyebrow">ACCEPTED / POSITION</span>
            <h3>Role adds useful context.</h3>
            <strong className="lab-score">
              4 / 4 <small>folds improved MAE</small>
            </strong>
            <ul>
              {folds.map((fold) => (
                <li key={fold.test}>
                  <span>{fold.test}</span>
                  <strong>{fullMoney(fold.positionMaeChange)}</strong>
                </li>
              ))}
            </ul>
            <p>
              Position minus four-feature MAE. Negative means error reduction;
              the improvement varies by season.
            </p>
          </article>
          <article>
            <span className="eyebrow">REJECTED / PER-90 FEATURES</span>
            <h3>Not every feature helps.</h3>
            <strong className="lab-score">
              4 / 4 <small>folds worsened MAE</small>
            </strong>
            <p>
              Goals / 90 and assists / 90 were tested alongside raw totals, then
              rejected from V1.
            </p>
            <dl>
              <div>
                <dt>Position baseline · pooled MAE</dt>
                <dd>{formatMoney(pooled.mae, 3)}</dd>
              </div>
              <div>
                <dt>Position + per-90 · pooled MAE</dt>
                <dd>{formatMoney(per90Pooled.mae, 3)}</dd>
              </div>
            </dl>
            <p>
              Useful-looking football features do not automatically improve
              predictive performance.
            </p>
          </article>
        </div>
      </section>
      <section
        className="analytics-section"
        id="importance"
        aria-labelledby="importance-title"
      >
        <span className="eyebrow">04 / INSIDE THE FROZEN V1 FIT</span>
        <h2 id="importance-title">What the splits found useful.</h2>
        <p className="analytics-intro">
          Normalized gain importance from the final all-data fit. This measures
          model split usefulness—not causal impact, a feature coefficient or the
          share of a player’s value caused by a feature.
        </p>
        <ImportanceChart />
        <p>
          Position family total:{" "}
          <strong>{modelHistory.positionFamilyGain.toFixed(9)}</strong>. The
          nine position indicators are shown separately; encoding affects how
          importance is allocated.
        </p>
      </section>
      <section className="analytics-section" aria-labelledby="limits-title">
        <span className="eyebrow">THE EDGE OF THE EVIDENCE</span>
        <h2 id="limits-title">A useful model. An incomplete picture.</h2>
        <div className="lab-limitations">
          {limitations.map(([title, text]) => (
            <article key={title}>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
        {current && (
          <details className="lab-sources">
            <summary>Current API model limitations</summary>
            <ul>
              {current.limitations.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          </details>
        )}
        <Link className="analytics-link" href="/rankings">
          Explore model-estimated differences ↗
        </Link>
      </section>
      <details className="lab-sources">
        <summary>Sources and evaluation provenance</summary>
        <p>
          Frozen research snapshot: MODEL_CARD_V1.md, individual model reports
          and TEMPORAL_BACKTESTING.md. Live registration is fetched separately.
        </p>
        <ul>
          {modelHistory.sources.map((source) => (
            <li key={source.path}>
              <code>{source.path}</code>
              <small>SHA-256 {source.sha256}</small>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
