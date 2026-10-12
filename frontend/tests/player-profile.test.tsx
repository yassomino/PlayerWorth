import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { PlayerProfile } from "@/components/player/PlayerProfile";
import { TransferSimulator } from "@/components/simulator/TransferSimulator";
import { ValuationHistory } from "@/components/player/ValuationHistory";
import { getPlayerPrediction, simulatePlayer } from "@/lib/api/client";
import type {
  PlayerDetail,
  PlayerPrediction,
  SimulationResponse,
} from "@/lib/api/types";
import {
  orderedSeasons,
  orderedValuations,
  parseDraft,
  draftFrom,
  seasonObservation,
} from "@/lib/player";
vi.mock("@/lib/api/client", () => ({
  getPlayerPrediction: vi.fn(),
  simulatePlayer: vi.fn(),
}));
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) =>
    children,
  LineChart: ({ data }: { data: unknown[] }) => (
    <div data-testid="chart-data">{JSON.stringify(data)}</div>
  ),
  Line: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));
const latest = {
  season: "2025/26",
  club: "Test Club",
  age: 25,
  position: "ST",
  appearances: 30,
  minutes: 2500,
  goals: 20,
  assists: 8,
  yellow_cards: 2,
  red_cards: 0,
  goals_per_90: 0.72,
  assists_per_90: 0.288,
  goal_contributions_per_90: 1.008,
  clubs_in_season: 1,
  season_end_date: "2026-05-24",
};
const data: PlayerDetail = {
  player: {
    id: 7,
    external_id: "test",
    name: "Example Player",
    position: "ST",
    nationality: null,
    image_url: null,
    latest_season: "2025/26",
    latest_known_club: "Test Club",
    date_of_birth: "2000-01-01",
  },
  seasons: [
    {
      ...latest,
      season: "2024/25",
      age: 24,
      goals: 10,
      season_end_date: "2025-05-25",
    },
    latest,
  ],
  market_values: [
    { value_eur: 20000000, value_date: "2026-06-03", source: "transfermarkt" },
    { value_eur: 18000000, value_date: "2025-05-30", source: "transfermarkt" },
  ],
};
const baseline: PlayerPrediction = {
  player_id: 7,
  season: "2025/26",
  model_name: "test-model",
  model_version: "1",
  prediction_id: null,
  input: { age: 25, minutes: 2500, goals: 20, assists: 8, position: "ST" },
  predicted_value_eur: 15000000,
  observed_value_eur: 20000000,
  difference_eur: -5000000,
};
const simulation: SimulationResponse = {
  ...baseline,
  baseline: { inputs: baseline.input, predicted_value_eur: 15000000 },
  simulation: {
    inputs: { ...baseline.input, goals: 21 },
    predicted_value_eur: 12000000,
  },
  difference_eur: -3000000,
};
beforeEach(() => {
  vi.mocked(getPlayerPrediction)
    .mockReset()
    .mockImplementation(async (_id, season) => ({
      ...baseline,
      season: season!,
      input: { ...baseline.input, goals: season === "2024/25" ? 10 : 20 },
    }));
  vi.mocked(simulatePlayer).mockReset().mockResolvedValue(simulation);
  window.history.replaceState(null, "", "/players/7");
});
test("profile defaults latest, displays real values and synchronizes explicit season", async () => {
  render(<PlayerProfile data={data} />);
  expect(screen.getByRole("heading", { name: "Example Player" })).toBeVisible();
  expect(screen.getByLabelText("Selected season")).toHaveValue("2025/26");
  expect(await screen.findByTestId("model-estimate")).toHaveTextContent("€15M");
  expect(screen.getAllByText("€20M").length).toBeGreaterThan(0);
  expect(screen.getByText(/below observed value/)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Selected season"), {
    target: { value: "2024/25" },
  });
  await waitFor(() => expect(screen.getByLabelText("Goals")).toHaveValue(10));
  expect(window.location.search).toContain("2024%2F25");
  expect(getPlayerPrediction).toHaveBeenLastCalledWith(
    7,
    "2024/25",
    expect.any(AbortSignal),
  );
});
test("deep link chooses its season", async () => {
  render(<PlayerProfile data={data} initialSeason="2024/25" />);
  expect(await screen.findByLabelText("Goals")).toHaveValue(10);
});
test("missing observed value is unavailable, never zero", async () => {
  vi.mocked(getPlayerPrediction).mockResolvedValue({
    ...baseline,
    observed_value_eur: null,
    difference_eur: null,
  });
  render(<PlayerProfile data={data} />);
  expect(await screen.findByText("Observed value unavailable")).toBeVisible();
  expect(document.querySelector(".pp-observed")).not.toHaveTextContent("€0");
});
test("prediction failure leaves stats and history available; retry works", async () => {
  vi.mocked(getPlayerPrediction).mockRejectedValueOnce(new Error("offline"));
  render(<PlayerProfile data={data} />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Estimate temporarily unavailable",
  );
  expect(
    screen.getByRole("heading", { name: "Market value history" }),
  ).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Retry estimate" }));
  expect(await screen.findByTestId("model-estimate")).toBeVisible();
});
test.each([
  ["Age", "26", { age: 26 }],
  ["Minutes", "5000", { minutes: 5000 }],
  ["Goals", "21", { goals: 21 }],
  ["Assists", "9", { assists: 9 }],
  ["Position", "W", { position: "W" }],
])(
  "explicit %s submission sends partial overrides only",
  async (label, value, overrides) => {
    render(<TransferSimulator baseline={baseline} />);
    fireEvent.change(screen.getByLabelText(label as string), {
      target: { value },
    });
    expect(simulatePlayer).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Update estimate/ }));
    await waitFor(() =>
      expect(simulatePlayer).toHaveBeenCalledWith(
        7,
        overrides,
        "2025/26",
        expect.any(AbortSignal),
      ),
    );
    expect(await screen.findByTestId("simulated-value")).toHaveTextContent(
      "€12M",
    );
    expect(screen.getByText("€15M")).toBeVisible();
    expect(screen.getByText(/below the original estimate/)).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: "Reset to season stats" }),
    );
    expect(screen.getByLabelText("Goals")).toHaveValue(20);
    expect(screen.getByLabelText("Position")).toHaveValue("ST");
    expect(screen.getByTestId("simulated-value")).toHaveTextContent("€15M");
    expect(simulatePlayer).toHaveBeenCalledTimes(1);
    expect(baseline.input).toEqual({
      age: 25,
      minutes: 2500,
      goals: 20,
      assists: 8,
      position: "ST",
    });
  },
);
test("stale simulation cannot replace edited or reset state", async () => {
  let finish!: (value: SimulationResponse) => void;
  vi.mocked(simulatePlayer).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  render(<TransferSimulator baseline={baseline} />);
  fireEvent.change(screen.getByLabelText("Goals"), { target: { value: "21" } });
  fireEvent.click(screen.getByRole("button", { name: /Update estimate/ }));
  fireEvent.click(
    screen.getByRole("button", { name: "Reset to season stats" }),
  );
  expect(vi.mocked(simulatePlayer).mock.calls[0][3]?.aborted).toBe(true);
  await act(async () => finish(simulation));
  expect(screen.getByTestId("simulated-value")).toHaveTextContent("€15M");
});
test("simulator error and invalid inputs preserve baseline", async () => {
  vi.mocked(simulatePlayer).mockRejectedValue(new Error("offline"));
  render(<TransferSimulator baseline={baseline} />);
  fireEvent.change(screen.getByLabelText("Goals"), { target: { value: "-1" } });
  expect(
    screen.getByRole("button", { name: /Update estimate/ }),
  ).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Goals"), { target: { value: "21" } });
  fireEvent.click(screen.getByRole("button", { name: /Update estimate/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Simulation unavailable",
  );
  expect(screen.getByText("€15M")).toBeVisible();
});
test.each(["", "-1", "Infinity", "1.5"])(
  "rejects invalid goals %s",
  (value) => {
    expect(
      parseDraft({ ...draftFrom(baseline.input), goals: value }).inputs,
    ).toBeNull();
  },
);
test("chart orders only supplied records and history sorts without mutation", () => {
  render(<ValuationHistory values={data.market_values} />);
  const chart = JSON.parse(screen.getByTestId("chart-data").textContent!);
  expect(chart.map((point: { value_eur: number }) => point.value_eur)).toEqual([
    18000000, 20000000,
  ]);
  expect(orderedSeasons(data.seasons)[0].season).toBe("2025/26");
  expect(data.seasons[0].season).toBe("2024/25");
  expect(orderedValuations(data.market_values)).toHaveLength(2);
  expect(seasonObservation(latest, data.market_values)?.value_eur).toBe(
    20000000,
  );
  expect(seasonObservation(latest, [])).toBeNull();
});
test("chart has a truthful empty state", () => {
  render(<ValuationHistory values={[]} />);
  expect(screen.getByText("No historical valuations available.")).toBeVisible();
  expect(screen.queryByTestId("chart-data")).not.toBeInTheDocument();
});

test("a late prediction from the previous season is discarded", async () => {
  let finish!: (value: PlayerPrediction) => void;
  vi.mocked(getPlayerPrediction).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  render(<PlayerProfile data={data} />);
  fireEvent.change(screen.getByLabelText("Selected season"), {
    target: { value: "2024/25" },
  });
  await screen.findByTestId("model-estimate");
  expect(vi.mocked(getPlayerPrediction).mock.calls[0][2]?.aborted).toBe(true);
  await act(async () => finish({ ...baseline, predicted_value_eur: 99000000 }));
  expect(screen.getByTestId("model-estimate")).toHaveTextContent("€15M");
  expect(screen.getByLabelText("Goals")).toHaveValue(10);
});

test.each([
  ["2026-05-23", false],
  ["2026-05-24", true],
  ["2026-07-08", true],
  ["2026-07-09", false],
])("history observation boundary %s", (date, accepted) => {
  expect(
    Boolean(
      seasonObservation(latest, [
        { value_eur: 1, value_date: date, source: "transfermarkt" },
      ]),
    ),
  ).toBe(accepted);
});
