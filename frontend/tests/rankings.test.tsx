import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { RankingsExplorer } from "@/components/rankings/RankingsExplorer";
import {
  getOvervaluedRankings,
  getUndervaluedRankings,
  ApiError,
} from "@/lib/api/client";
import type { RankingResponse } from "@/lib/api/types";
import {
  rankingSelection,
  rankingsUrl,
  validRankingSelection,
} from "@/lib/rankings";
vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  getOvervaluedRankings: vi.fn(),
  getUndervaluedRankings: vi.fn(),
}));
const above: RankingResponse = {
  model_name: "model-from-api",
  model_version: "1",
  season: "2025/26",
  eligible_rows: 50,
  excluded_rows: 2,
  description: "Model-estimated difference",
  items: [
    {
      rank: 1,
      player_id: 97,
      player_name: "First Player",
      club: "Club A",
      position: "ST",
      season: "2025/26",
      observed_value_eur: 10000000,
      predicted_value_eur: 30000000,
      difference_eur: 20000000,
    },
    {
      rank: 2,
      player_id: 31,
      player_name: "Second Player",
      club: null,
      position: null,
      season: "2025/26",
      observed_value_eur: 10000000,
      predicted_value_eur: 25000000,
      difference_eur: 15000000,
    },
  ],
};
const below: RankingResponse = {
  ...above,
  items: above.items.map((row, i) => ({
    ...row,
    predicted_value_eur: i * 1000000,
    difference_eur: i * 1000000 - row.observed_value_eur,
  })),
};
beforeEach(() => {
  vi.mocked(getUndervaluedRankings).mockReset().mockResolvedValue(above);
  vi.mocked(getOvervaluedRankings).mockReset().mockResolvedValue(below);
  window.history.replaceState(null, "", "/rankings");
});
function show(query = "") {
  render(
    <RankingsExplorer
      initialSelection={rankingSelection(new URLSearchParams(query))}
    />,
  );
}
test("default latest, real API order, links, money and descriptive disclaimer", async () => {
  show();
  expect(screen.getByLabelText("Season")).toHaveValue("2025/26");
  expect(screen.getByLabelText("Loading data")).toBeVisible();
  await screen.findByRole("table");
  expect(getUndervaluedRankings).toHaveBeenCalledWith(
    20,
    "2025/26",
    expect.any(AbortSignal),
  );
  expect(getOvervaluedRankings).not.toHaveBeenCalled();
  const links = screen.getAllByRole("link", { name: /Player/ });
  expect(links[0]).toHaveTextContent("First Player");
  expect(links[1]).toHaveTextContent("Second Player");
  expect(links[0]).toHaveAttribute("href", "/players/97?season=2025%2F26");
  expect(screen.getByText("+€20M")).toBeVisible();
  expect(
    screen.getAllByText("Model estimate above observed value"),
  ).toHaveLength(2);
  expect(screen.getByText(/not objective player valuations/)).toBeVisible();
  expect(screen.getByText(/not unseen-season evaluation/)).toBeVisible();
});
test("direction and season update URL and request only the selected list", async () => {
  show();
  await screen.findByRole("table");
  fireEvent.click(screen.getByRole("button", { name: /Model Below Observed/ }));
  expect(await screen.findByText("-€10M")).toBeVisible();
  expect(window.location.search).toContain("direction=below");
  expect(getUndervaluedRankings).toHaveBeenCalledTimes(1);
  expect(getOvervaluedRankings).toHaveBeenCalledWith(
    20,
    "2025/26",
    expect.any(AbortSignal),
  );
  expect(
    within(screen.getByRole("table")).getAllByRole("row")[1],
  ).toHaveTextContent("-€10M");
  fireEvent.change(screen.getByLabelText("Season"), {
    target: { value: "2023/24" },
  });
  await waitFor(() =>
    expect(getOvervaluedRankings).toHaveBeenLastCalledWith(
      20,
      "2023/24",
      expect.any(AbortSignal),
    ),
  );
  expect(window.location.search).toContain("season=2023%2F24");
});
test("deep link and popstate restore controls", async () => {
  show("season=2024%2F25&direction=below");
  await screen.findByRole("table");
  expect(screen.getByLabelText("Season")).toHaveValue("2024/25");
  expect(
    screen.getByRole("button", { name: /Model Below Observed/ }),
  ).toHaveAttribute("aria-pressed", "true");
  act(() => {
    window.history.replaceState(
      null,
      "",
      "/rankings?season=2022%2F23&direction=above",
    );
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  await waitFor(() =>
    expect(getUndervaluedRankings).toHaveBeenLastCalledWith(
      20,
      "2022/23",
      expect.any(AbortSignal),
    ),
  );
});
test("invalid and duplicate queries do not load a substitute ranking", () => {
  show("season=1990%2F91&direction=sideways");
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Unavailable ranking selection",
  );
  expect(getUndervaluedRankings).not.toHaveBeenCalled();
  expect(getOvervaluedRankings).not.toHaveBeenCalled();
  expect(
    validRankingSelection(
      rankingSelection(new URLSearchParams("season=2025/26&season=2024/25")),
    ),
  ).toBe(false);
  expect(rankingsUrl({ season: "2025/26", direction: "above" })).toBe(
    "/rankings?season=2025%2F26&direction=above",
  );
});
test("empty response is explicit", async () => {
  vi.mocked(getUndervaluedRankings).mockResolvedValue({ ...above, items: [] });
  show();
  expect(
    await screen.findByRole("heading", { name: "No matching ranking rows" }),
  ).toBeVisible();
});
test.each([404, 422, 503, 500])(
  "safe error for %s, with working retry",
  async (status) => {
    vi.mocked(getUndervaluedRankings).mockRejectedValueOnce(
      new ApiError(status, "private backend detail"),
    );
    show();
    expect(await screen.findByRole("alert")).not.toHaveTextContent(
      "private backend detail",
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry rankings" }));
    expect(await screen.findByRole("table")).toBeVisible();
  },
);
test("late response from old direction cannot replace the selected ranking", async () => {
  let finish!: (result: RankingResponse) => void;
  vi.mocked(getUndervaluedRankings).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  show();
  fireEvent.click(screen.getByRole("button", { name: /Model Below Observed/ }));
  await screen.findByText("-€10M");
  expect(vi.mocked(getUndervaluedRankings).mock.calls[0][2]?.aborted).toBe(
    true,
  );
  await act(async () => finish(above));
  expect(screen.queryByText("+€20M")).not.toBeInTheDocument();
  expect(screen.getByText("-€10M")).toBeVisible();
});
