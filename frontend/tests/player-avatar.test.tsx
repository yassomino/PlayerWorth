import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import {
  PlayerAvatar,
  playerMonogram,
  positionFamily,
} from "@/components/player/PlayerAvatar";
import { PlayerHeader } from "@/components/player/PlayerHeader";
import type { PlayerDetail, PlayerSeason } from "@/lib/api/types";

test.each([
  ["Erling Haaland", "EH"],
  ["Cole Palmer", "CP"],
  ["Mohamed Salah", "MS"],
  ["  cole   palmer  ", "CP"],
  ["Hannibal", "H"],
  ["Kevin De Bruyne", "KB"],
  ["João Pedro Junqueira de Jesus", "JJ"],
  ["—", "—"],
  ["   ", "—"],
  ["Éder Militão", "ÉM"],
])("monogram for %s is %s", (name, initials) => {
  expect(playerMonogram(name)).toBe(initials);
});

test.each([
  [" gk ", "GK"],
  ["Goalkeeper", "GK"],
  ["CB", "DEF"],
  ["LB", "DEF"],
  ["RB", "DEF"],
  ["FB", "DEF"],
  ["WB", "DEF"],
  ["LWB", "DEF"],
  ["RWB", "DEF"],
  ["Centre-Back", "DEF"],
  ["DM", "MID"],
  ["CM", "MID"],
  ["AM", "MID"],
  ["LM", "MID"],
  ["RM", "MID"],
  ["Central   Midfield", "MID"],
  ["ST", "ATT"],
  ["CF", "ATT"],
  ["W", "ATT"],
  ["LW", "ATT"],
  ["RW", "ATT"],
  ["Left Winger", "ATT"],
  [null, "UNKNOWN"],
  [undefined, "UNKNOWN"],
  ["", "UNKNOWN"],
  ["unknown provider role", "UNKNOWN"],
  ["constructor", "UNKNOWN"],
])("position %s maps conservatively to %s", (position, family) => {
  expect(positionFamily(position)).toBe(family);
});

test.each(["xs", "sm", "md", "hero"] as const)(
  "%s remains decorative beside the player's name",
  (size) => {
    const { container } = render(
      <PlayerAvatar name="Erling Haaland" position="ST" size={size} />,
    );
    const tile = container.firstElementChild!;
    expect(tile).toHaveAttribute("aria-hidden", "true");
    expect(tile).toHaveAttribute("data-size", size);
    expect(tile).toHaveAttribute("data-family", "ATT");
    expect(tile).toHaveTextContent("EH");
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByText("ST") !== null).toBe(size !== "xs");
  },
);

test("unknown long positions stay available without becoming overflowing labels", () => {
  const position = "An unrecognized provider position with many words";
  const { container } = render(
    <PlayerAvatar name="Single" position={position} />,
  );
  expect(container.firstElementChild).toHaveAttribute("title", position);
  expect(container.firstElementChild).toHaveAttribute("data-family", "UNKNOWN");
  expect(container.firstElementChild).toHaveTextContent("S—");
});

test("dossier portrait follows selected-season position and falls back to player position", () => {
  const player: PlayerDetail["player"] = {
    id: 1,
    external_id: "1",
    name: "Test Player",
    position: "CB",
    nationality: null,
    image_url: null,
    date_of_birth: null,
    latest_season: null,
    latest_known_club: null,
  };
  const season = {
    position: "CM",
    season: "2024/25",
    club: "Test Club",
    age: 24,
  } as PlayerSeason;
  const { container, rerender } = render(
    <PlayerHeader player={player} season={season} />,
  );
  expect(container.querySelector('[data-size="hero"]')).toHaveAttribute(
    "data-family",
    "MID",
  );
  rerender(<PlayerHeader player={player} />);
  expect(container.querySelector('[data-size="hero"]')).toHaveAttribute(
    "data-family",
    "DEF",
  );
  expect(screen.getByRole("heading", { name: "Test Player" })).toBeVisible();
});
