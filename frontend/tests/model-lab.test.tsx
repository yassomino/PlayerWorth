import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import { ModelLab } from "@/components/model/ModelLab";
import { modelHistory } from "@/lib/model-history";
import type { ModelResponse } from "@/lib/api/types";

const current: ModelResponse = {
  model_name: "live-test-model",
  model_version: "2.3.4",
  model_type: "xgboost.XGBRegressor",
  feature_list: ["age", "minutes", "goals", "assists", "position"],
  evaluation_method: "temporal OOF evidence",
  mae: 1234567,
  rmse: 2345678,
  r2: 0.4,
  median_absolute_error: 1000000,
  is_production: true,
  training_seasons: ["2021/22", "2022/23"],
  training_row_count: 100,
  evaluation_row_count: 40,
  limitations: ["Live limitation"],
};
test("Model Lab distinguishes live registration from frozen experiment history", () => {
  render(<ModelLab current={current} registered={[current]} />);
  const registry = screen.getByLabelText("Current registered model");
  expect(within(registry).getByText("live-test-model")).toBeVisible();
  expect(registry).toHaveTextContent("v2.3.4");
  expect(registry).toHaveTextContent("€1.23M");
  expect(registry).toHaveTextContent("1 registered model version");
  expect(
    screen.getByRole("heading", {
      name: "Exploratory 2025/26 held-out-season comparison",
    }),
  ).toBeVisible();
  expect(
    screen.getByRole("heading", {
      name: "Temporal pooled out-of-fold evaluation",
    }),
  ).toBeVisible();
  expect(
    screen.getByText(/not fully nested historical model selection/),
  ).toBeVisible();
});
test("all evolution stages, exact comparison metrics and experimental decisions render", () => {
  render(<ModelLab current={current} registered={[current]} />);
  const table = screen.getByRole("table");
  expect(within(table).getAllByRole("row")).toHaveLength(6);
  expect(table).toHaveTextContent("€11,090,195.65");
  expect(table).toHaveTextContent("0.452857243619");
  expect(table).toHaveTextContent("€9,993,665.91");
  expect(
    screen.getByText("Regularization did not improve held-out performance."),
  ).toBeVisible();
  expect(screen.getByText(/Nonlinearity mattered/)).toHaveTextContent("8.6%");
  expect(
    screen.getByText("A small additional improvement over Random Forest."),
  ).toBeVisible();
  expect(screen.getByText("folds improved MAE")).toBeVisible();
  expect(screen.getByText("folds worsened MAE")).toBeVisible();
  expect(screen.getByText(/then rejected from V1/)).toBeVisible();
  expect(screen.getByText("€9.75M")).toBeVisible();
  expect(screen.getByText("€9,677,493.91")).toBeVisible();
  expect(screen.getByText(/accuracy percentage/)).toHaveTextContent(
    "not an accuracy percentage",
  );
});
test("temporal folds, complete gain chart and limitations are accessible", () => {
  render(<ModelLab current={current} registered={[current]} />);
  for (const fold of [1, 2, 3, 4])
    expect(screen.getByText(`FOLD ${fold}`)).toBeVisible();
  const figure = screen.getByRole("figure");
  expect(within(figure).getAllByRole("listitem")).toHaveLength(13);
  expect(figure).toHaveTextContent("position_UNKNOWN");
  expect(figure).toHaveTextContent("0.284789");
  expect(screen.getByText(/not causal impact/i)).toBeVisible();
  expect(screen.getByText(/No contract length, injuries/)).toBeVisible();
  expect(
    screen.getByText(/Superstar extrapolation remains difficult/),
  ).toBeVisible();
  expect(
    screen.getByRole("heading", { name: "Premier League only" }),
  ).toBeVisible();
});
test("API outages never replace current metadata with frozen experiment values", () => {
  render(<ModelLab current={null} registered={null} />);
  expect(screen.getByRole("status")).toHaveTextContent(
    "Current model temporarily unavailable",
  );
  expect(screen.getByText("Registry list unavailable.")).toBeVisible();
  expect(screen.getByRole("table")).toHaveTextContent("€10,135,335.82");
});
test("frozen protocol, feature and fold records remain distinct", () => {
  expect(modelHistory.experiments.map((row) => row.protocol)).toEqual(
    Array(5).fill("exploratory-2025/26"),
  );
  expect(modelHistory.experiments.map((row) => row.features)).toEqual([
    4, 4, 4, 4, 5,
  ]);
  expect(modelHistory.folds.map((row) => row.train.length)).toEqual([
    1, 2, 3, 4,
  ]);
  expect(
    modelHistory.folds.every((row) =>
      row.train.every((season) => season < row.test),
    ),
  ).toBe(true);
  expect(modelHistory.folds.every((row) => row.positionMaeChange < 0)).toBe(
    true,
  );
  expect(modelHistory.pooled.rows).toBe(2103);
  expect(modelHistory.per90Pooled.mae).toBeGreaterThan(modelHistory.pooled.mae);
  expect(
    modelHistory.importance
      .filter((row) => row.feature.startsWith("position_"))
      .reduce((sum, row) => sum + row.gain, 0),
  ).toBeCloseTo(modelHistory.positionFamilyGain, 12);
});
