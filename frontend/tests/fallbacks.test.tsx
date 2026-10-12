import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ModelSnapshot } from "@/components/home/ModelSnapshot";
import { RankingsPreview } from "@/components/home/RankingsPreview";
vi.mock("@/lib/api/client", () => ({
  getCurrentModel: vi.fn().mockRejectedValue(new Error("private error")),
  getUndervaluedRankings: vi.fn().mockRejectedValue(new Error("private error")),
  getOvervaluedRankings: vi.fn().mockRejectedValue(new Error("private error")),
}));
test("secondary sections fail independently with safe messages", async () => {
  render(
    <>
      {await ModelSnapshot()}
      {await RankingsPreview({ direction: "higher" })}
      <p>Search remains available</p>
    </>,
  );
  expect(
    screen.getByText("Model snapshot is temporarily unavailable."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Ranking data isn't available right now."),
  ).toBeInTheDocument();
  expect(screen.getByText("Search remains available")).toBeInTheDocument();
  expect(screen.queryByText("private error")).not.toBeInTheDocument();
});
