import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { PlayerSearch } from "@/components/search/PlayerSearch";
import { renderToString } from "react-dom/server";
import { searchPlayers } from "@/lib/api/client";
const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api/client", () => ({ searchPlayers: vi.fn() }));
afterEach(() => vi.useRealTimers());
const response = {
  items: [
    {
      id: 582,
      external_id: "418560",
      name: "Erling Haaland",
      position: "ST",
      nationality: null,
      image_url: null,
      latest_season: "2025/26",
      latest_known_club: "Manchester City",
    },
  ],
  limit: 8,
  offset: 0,
};

test("server-rendered search waits for interactive hydration", () => {
  const html = renderToString(<PlayerSearch />);
  const document = new DOMParser().parseFromString(html, "text/html");
  expect(document.querySelector("input")?.disabled).toBe(true);
  render(<PlayerSearch />);
  expect(screen.getByRole("combobox")).toBeEnabled();
});
async function typeQuery(text = "haaland") {
  fireEvent.change(screen.getByRole("combobox"), { target: { value: text } });
  await act(async () => {
    vi.advanceTimersByTime(300);
  });
}
test("debounces, renders internal ID links and supports keyboard", async () => {
  vi.useFakeTimers();
  vi.mocked(searchPlayers).mockResolvedValue(response);
  render(<PlayerSearch />);
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "h" } });
  await act(async () => {
    vi.advanceTimersByTime(300);
  });
  expect(searchPlayers).not.toHaveBeenCalled();
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "ha" } });
  await act(async () => {
    vi.advanceTimersByTime(299);
  });
  expect(searchPlayers).not.toHaveBeenCalled();
  await act(async () => {
    vi.advanceTimersByTime(1);
  });
  expect(screen.getByText("Erling Haaland")).toBeInTheDocument();
  expect(
    screen.getByRole("option", { name: /Erling Haaland/ }),
  ).toHaveAttribute("href", "/players/582");
  fireEvent.keyDown(screen.getByRole("combobox"), { key: "ArrowDown" });
  expect(screen.getByRole("option")).toHaveAttribute("aria-selected", "true");
  fireEvent.keyDown(screen.getByRole("combobox"), { key: "Enter" });
  expect(push).toHaveBeenCalledWith("/players/582");
});
test("empty and error states", async () => {
  vi.useFakeTimers();
  vi.mocked(searchPlayers).mockResolvedValue({
    items: [],
    limit: 8,
    offset: 0,
  });
  render(<PlayerSearch />);
  await typeQuery("xyz");
  expect(screen.getByText("No players found for 'xyz'.")).toBeInTheDocument();
  vi.mocked(searchPlayers).mockRejectedValue(new Error());
  await typeQuery("error");
  expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load players");
});
test("escape closes and changed query aborts old request", async () => {
  vi.useFakeTimers();
  vi.mocked(searchPlayers).mockResolvedValue(response);
  render(<PlayerSearch />);
  await typeQuery();
  const signal = vi.mocked(searchPlayers).mock.calls.at(-1)![1];
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "other" },
  });
  expect(signal?.aborted).toBe(true);
  fireEvent.keyDown(screen.getByRole("combobox"), { key: "Escape" });
  expect(screen.getByRole("combobox")).toHaveAttribute(
    "aria-expanded",
    "false",
  );
});
