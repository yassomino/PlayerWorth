"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState, useSyncExternalStore } from "react";
import { searchPlayers } from "@/lib/api/client";
import type { PlayerSearchResult } from "@/lib/api/types";
import { PlayerAvatar } from "../player/PlayerAvatar";
import { Skeleton } from "../ui/States";

const subscribeToHydration = () => () => {};

export function PlayerSearch() {
  // Do not accept keystrokes before React can handle the controlled input.
  const hydrated = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false,
  );
  const router = useRouter();
  const id = useId();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlayerSearchResult[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  useEffect(() => {
    if (query.trim().length < 2) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const data = await searchPlayers(query.trim(), controller.signal);
        if (!controller.signal.aborted) {
          setResults(data.items);
          setStatus("ready");
        }
      } catch {
        if (!controller.signal.aborted) setStatus("error");
      }
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);
  const expanded = open && query.trim().length >= 2;
  return (
    <div
      className="search"
      id="player-search"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <label htmlFor={id} className="eyebrow search-label">
        START WITH A PLAYER
      </label>
      <div className="search-control">
        <svg
          aria-hidden="true"
          width="23"
          height="23"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
        >
          <circle cx="10.5" cy="10.5" r="6.5" />
          <path d="m16 16 5 5" />
        </svg>
        <input
          id={id}
          disabled={!hydrated}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={expanded}
          aria-controls={`${id}-results`}
          aria-activedescendant={
            active >= 0 && expanded ? `${id}-option-${active}` : undefined
          }
          autoComplete="off"
          placeholder="Search a Premier League player"
          value={query}
          onChange={(event) => {
            const value = event.target.value;
            setQuery(value);
            setResults([]);
            setActive(-1);
            setOpen(true);
            setStatus(value.trim().length >= 2 ? "loading" : "idle");
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setOpen(false);
              setActive(-1);
            }
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault();
              setOpen(true);
              setActive((index) =>
                results.length
                  ? index === -1
                    ? event.key === "ArrowDown"
                      ? 0
                      : results.length - 1
                    : (index +
                        (event.key === "ArrowDown" ? 1 : -1) +
                        results.length) %
                      results.length
                  : -1,
              );
            }
            if (event.key === "Enter" && expanded && results.length) {
              event.preventDefault();
              router.push(`/players/${results[active >= 0 ? active : 0].id}`);
              setOpen(false);
            }
          }}
        />
        <span className="search-arrow" aria-hidden="true">
          ↗
        </span>
      </div>
      <p className="search-hint">
        Search by name <span>·</span> Premier League, 2021/22–2025/26
      </p>
      {expanded && (
        <div className="search-dropdown">
          {status === "loading" && <Skeleton rows={2} />}
          <p className="sr-only" role="status">
            {status === "ready"
              ? `${results.length} players found.`
              : status === "error"
                ? "Couldn't load players."
                : "Searching players…"}
          </p>
          {status === "error" && (
            <p className="search-message" role="alert">
              Couldn&apos;t load players. Please try searching again.
            </p>
          )}
          {status === "ready" && !results.length && (
            <p className="search-message">
              No players found for &apos;{query}&apos;.
            </p>
          )}
          <ul id={`${id}-results`} role="listbox" aria-label="Player results">
            {results.map((player, index) => (
              <li
                key={player.id}
                role="presentation"
                className={active === index ? "active" : ""}
              >
                <Link
                  id={`${id}-option-${index}`}
                  role="option"
                  aria-selected={active === index}
                  href={`/players/${player.id}`}
                  tabIndex={-1}
                  onMouseEnter={() => setActive(index)}
                  onClick={() => setOpen(false)}
                >
                  <PlayerAvatar
                    name={player.name}
                    position={player.position}
                    size="xs"
                  />
                  <span className="result-info">
                    <strong>{player.name}</strong>
                    <span>
                      {player.latest_known_club ?? "Club unavailable"} ·{" "}
                      {player.latest_season ?? "Season unavailable"}
                    </span>
                  </span>
                  <span className="position">{player.position ?? "—"}</span>
                  <span aria-hidden="true">↗</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
