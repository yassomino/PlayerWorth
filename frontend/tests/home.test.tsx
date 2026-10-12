import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { ModelSnapshotView } from "@/components/home/ModelSnapshot";
import {
  RankingCard,
  RankingDisclaimer,
} from "@/components/home/RankingsPreview";
import type { ModelResponse, RankingResponse } from "@/lib/api/types";
test("model API shape and evaluation scope", () => {
  const model: ModelResponse = {
    model_name: "playerworth_v1",
    model_version: "1.0.0",
    model_type: "xgboost.XGBRegressor",
    feature_list: ["age", "minutes", "goals", "assists", "position"],
    evaluation_method: "temporal out-of-fold",
    mae: 9677493.908571832,
    rmse: 15046414.97117625,
    r2: 0.5251604485,
    median_absolute_error: 5881224,
    is_production: true,
    training_seasons: ["2021/22", "2022/23", "2023/24", "2024/25", "2025/26"],
    training_row_count: 2594,
    evaluation_row_count: 2103,
    limitations: [],
  };
  render(<ModelSnapshotView model={model} />);
  expect(screen.getByText("€9.68M")).toBeInTheDocument();
  expect(screen.getByText("TEMPORAL OOF MAE")).toBeInTheDocument();
  expect(screen.getByText("0.525")).toBeInTheDocument();
  expect(screen.getByText("2,594")).toBeInTheDocument();
});
test.each([
  ["higher", 29286296, "+€29.3M"],
  ["lower", -70381864, "-€70.4M"],
] as const)("ranking %s", (direction, difference, formatted) => {
  const data: RankingResponse = {
    model_name: "test",
    model_version: "1",
    season: "2025/26",
    eligible_rows: 1,
    excluded_rows: 0,
    description: "model difference",
    items: [
      {
        rank: 1,
        player_id: 962,
        player_name: "Fixture Player",
        club: "Fixture Club",
        position: "ST",
        season: "2025/26",
        observed_value_eur: 65000000,
        predicted_value_eur: 65000000 + difference,
        difference_eur: difference,
      },
    ],
  };
  render(
    <>
      <RankingCard data={data} direction={direction} />
      <RankingDisclaimer />
    </>,
  );
  expect(screen.getByText(formatted)).toBeInTheDocument();
  expect(screen.getByRole("link")).toHaveAttribute("href", "/players/962");
  expect(
    screen.getByText(/not objective transfer valuations/),
  ).toBeInTheDocument();
});
