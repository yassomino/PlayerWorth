import type { MarketValue, ModelInputs, PlayerSeason } from "./api/types";

export const orderedSeasons = (seasons: PlayerSeason[]) =>
  [...seasons].sort((a, b) => b.season.localeCompare(a.season));
export const orderedValuations = (values: MarketValue[]) =>
  [...values].sort(
    (a, b) =>
      a.value_date.localeCompare(b.value_date) ||
      a.source.localeCompare(b.source),
  );

/** Display alignment only: same inclusive 0..45-day Transfermarkt policy as the API. */
export function seasonObservation(
  season: PlayerSeason,
  values: MarketValue[],
): MarketValue | null {
  const end = Date.parse(season.season_end_date);
  return (
    orderedValuations(values).find(
      (value) =>
        value.source === "transfermarkt" &&
        Date.parse(value.value_date) >= end &&
        Date.parse(value.value_date) <= end + 45 * 86400000,
    ) ?? null
  );
}

export type Draft = {
  age: string;
  minutes: string;
  goals: string;
  assists: string;
  position: string | null;
};
export const draftFrom = (inputs: ModelInputs): Draft => ({
  age: String(inputs.age),
  minutes: String(inputs.minutes),
  goals: String(inputs.goals),
  assists: String(inputs.assists),
  position: inputs.position,
});
export function parseDraft(draft: Draft): {
  inputs: ModelInputs | null;
  errors: Partial<Record<keyof ModelInputs, string>>;
} {
  const errors: Partial<Record<keyof ModelInputs, string>> = {};
  const numbers = { age: 0, minutes: 0, goals: 0, assists: 0 };
  for (const key of ["age", "minutes", "goals", "assists"] as const) {
    const value = Number(draft[key]);
    if (!draft[key].trim() || !Number.isFinite(value) || value < 0)
      errors[key] = "Enter a finite number of zero or more.";
    else if ((key === "goals" || key === "assists") && !Number.isInteger(value))
      errors[key] = "Enter a whole number of zero or more.";
    numbers[key] = value;
  }
  return {
    inputs: Object.keys(errors).length
      ? null
      : { ...numbers, position: draft.position },
    errors,
  };
}
export function changedInputs(
  original: ModelInputs,
  next: ModelInputs,
): Partial<ModelInputs> {
  const changes: Partial<ModelInputs> = {};
  for (const key of ["age", "minutes", "goals", "assists"] as const)
    if (next[key] !== original[key]) changes[key] = next[key];
  if (next.position !== original.position) changes.position = next.position;
  return changes;
}
