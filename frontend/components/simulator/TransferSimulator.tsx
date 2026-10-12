"use client";
import { useEffect, useRef, useState } from "react";
import { simulatePlayer } from "@/lib/api/client";
import type { PlayerPrediction, SimulationResponse } from "@/lib/api/types";
import { changedInputs, draftFrom, parseDraft, type Draft } from "@/lib/player";
import { formatMoney, fullMoney } from "@/lib/format";
import { ValueDelta } from "../player/ValueDelta";

const positions = ["GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"];
const controls = [
  { key: "age", label: "Age", max: 45 },
  { key: "minutes", label: "Minutes", max: 4500 },
  { key: "goals", label: "Goals", max: 50 },
  { key: "assists", label: "Assists", max: 30 },
] as const;

export function TransferSimulator({
  baseline,
}: {
  baseline: PlayerPrediction;
}) {
  const [draft, setDraft] = useState<Draft>(() => draftFrom(baseline.input));
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  const { inputs, errors } = parseDraft(draft);
  const overrides = inputs ? changedInputs(baseline.input, inputs) : null;
  const changed = overrides !== null && Object.keys(overrides).length > 0;
  const displayed =
    result?.simulation.predicted_value_eur ??
    (!changed && inputs ? baseline.predicted_value_eur : null);
  function edit(key: keyof Draft, value: string | null) {
    pending.current?.abort();
    setBusy(false);
    setError(null);
    setResult(null);
    setDraft((current) => ({ ...current, [key]: value }));
  }
  function reset() {
    pending.current?.abort();
    setDraft(draftFrom(baseline.input));
    setResult(null);
    setBusy(false);
    setError(null);
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!inputs || !overrides || !changed || busy) return;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await simulatePlayer(
        baseline.player_id,
        overrides,
        baseline.season,
        controller.signal,
      );
      if (!controller.signal.aborted) setResult(response);
    } catch {
      if (!controller.signal.aborted)
        setError(
          "Simulation unavailable. Your season data is unchanged. Please try again.",
        );
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <section
      className="pp-simulator"
      id="simulator"
      aria-labelledby="simulator-title"
    >
      <div className="pp-section-title">
        <span className="eyebrow">
          CHANGE THE INPUTS. EXPLORE THE RESPONSE.
        </span>
        <h2 id="simulator-title">
          Transfer Simulator
          <span className="pp-section-index" aria-hidden="true">
            ↗
          </span>
        </h2>
        <p className="pp-note">
          Start with {baseline.season}. Change a scenario, not the player&apos;s
          record.
        </p>
      </div>
      <div className="pp-simulator-grid">
        <form onSubmit={submit} noValidate>
          <div className="pp-controls">
            {controls.map(({ key, label, max }) => (
              <div className="pp-control" key={key}>
                <div className="pp-control-label">
                  <label htmlFor={`sim-${key}`}>{label}</label>
                  <input
                    id={`sim-${key}`}
                    type="number"
                    min={0}
                    step={key === "goals" || key === "assists" ? 1 : "any"}
                    value={draft[key]}
                    onChange={(event) => edit(key, event.target.value)}
                    aria-invalid={Boolean(errors[key])}
                    aria-describedby={
                      errors[key] ? `sim-${key}-error` : undefined
                    }
                  />
                </div>
                <input
                  type="range"
                  min={0}
                  max={Math.max(
                    max,
                    Number(draft[key]) || 0,
                    baseline.input[key],
                  )}
                  step={1}
                  value={Math.max(0, Number(draft[key]) || 0)}
                  onChange={(event) => edit(key, event.target.value)}
                  aria-label={`${label} slider`}
                />
                {errors[key] && (
                  <p className="pp-field-error" id={`sim-${key}-error`}>
                    {errors[key]}
                  </p>
                )}
              </div>
            ))}
            <div className="pp-position-control">
              <label htmlFor="sim-position">Position</label>
              <select
                id="sim-position"
                value={draft.position ?? ""}
                onChange={(event) =>
                  edit("position", event.target.value || null)
                }
              >
                {!positions.includes(baseline.input.position ?? "") && (
                  <option value={baseline.input.position ?? ""}>
                    {baseline.input.position ?? "Unmapped / unknown"} (stored)
                  </option>
                )}
                {positions.map((position) => (
                  <option key={position}>{position}</option>
                ))}
              </select>
            </div>
          </div>
          <p className="pp-note">
            Sliders cover common ranges. Manual entry accepts any finite,
            nonnegative value; goals and assists must be whole numbers.
          </p>
          <div className="pp-form-actions">
            <button
              type="submit"
              className="pp-button"
              disabled={!inputs || !changed || busy}
            >
              {busy ? "Updating…" : "Update estimate"}{" "}
              <span aria-hidden="true">↗</span>
            </button>
            <button type="button" className="pp-reset" onClick={reset}>
              Reset to season stats
            </button>
          </div>
        </form>
        <div className="pp-sim-output" aria-live="polite" aria-busy={busy}>
          <span className="eyebrow">YOUR SCENARIO / {baseline.season}</span>
          <div className="pp-baseline">
            <span>Original model estimate</span>
            <strong title={fullMoney(baseline.predicted_value_eur)}>
              {formatMoney(baseline.predicted_value_eur)}
            </strong>
          </div>
          <div className="pp-sim-estimate">
            <span>Simulated model estimate</span>
            <strong
              title={displayed === null ? undefined : fullMoney(displayed)}
              data-testid="simulated-value"
            >
              {busy ? "…" : displayed === null ? "—" : formatMoney(displayed)}
            </strong>
          </div>
          {error ? (
            <p role="alert" className="pp-field-error">
              {error}
            </p>
          ) : busy ? (
            <p className="pp-note">Calculating with the model…</p>
          ) : displayed === null ? (
            <p className="pp-note">
              {inputs
                ? "Inputs changed. Update the estimate to see the model’s response."
                : "Check your inputs before updating."}
            </p>
          ) : (
            <ValueDelta
              value={result?.difference_eur ?? 0}
              comparison="the original estimate"
            />
          )}
          <p className="pp-note">
            {baseline.model_name} · v{baseline.model_version}
            <br />
            Hypothetical · not saved
          </p>
        </div>
      </div>
      <p className="pp-simulation-warning">
        Simulations show how the trained model responds to hypothetical inputs.
        They do not represent causal effects or guaranteed changes in a
        player&apos;s market value. More goals or assists do not necessarily
        produce a higher estimate.
      </p>
    </section>
  );
}
